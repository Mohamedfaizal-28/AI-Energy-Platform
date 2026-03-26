import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import firebase_admin
from firebase_admin import credentials, db
import time

# ══════════════════════════════════════════════
# FIREBASE INIT (runs only once)
# ══════════════════════════════════════════════
# pip install firebase-admin

FIREBASE_DB_URL = "https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/"

if not firebase_admin._apps:
    # For Streamlit Cloud deployment: use service account JSON
    # Download from Firebase Console → Project Settings → Service accounts → Generate new private key
    # Save as "firebase_key.json" in same folder as app.py
    try:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
    except Exception:
        # Fallback: no credentials (read-only public rules)
        firebase_admin.initialize_app(options={'databaseURL': FIREBASE_DB_URL})

def get_sensor_data():
    """Read live sensor data pushed by ESP32"""
    try:
        ref = db.reference('/sensors')
        data = ref.get()
        return data if data else {}
    except Exception as e:
        return {}

def set_relay(relay_num, state):
    """Send relay command to ESP32 via Firebase"""
    try:
        ref = db.reference(f'/relays/relay{relay_num}')
        ref.set(1 if state else 0)
        return True
    except Exception as e:
        return False

def get_relay_states():
    """Read current relay states from Firebase"""
    try:
        ref = db.reference('/relays')
        return ref.get() or {}
    except Exception:
        return {}

# ══════════════════════════════════════════════
# LOGIN SYSTEM
# ══════════════════════════════════════════════

def check_login(username, password):
    return username == "admin" and password == "1234"

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.title("🔐 AI Energy Platform Login")
    user = st.text_input("Username")
    pwd  = st.text_input("Password", type="password")
    if st.button("Login"):
        if check_login(user, pwd):
            st.session_state.role = "admin"
            st.success("Admin Login Successful")
            st.rerun()
        else:
            st.session_state.role = "user"
            st.success("User Mode Access Granted")
            st.rerun()
    st.stop()

# ══════════════════════════════════════════════
# DATABASE SETUP
# ══════════════════════════════════════════════

conn   = sqlite3.connect("energy_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS energy_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    hour INTEGER,
    voltage REAL,
    current REAL,
    temperature REAL,
    predicted_load REAL,
    status TEXT
)
""")
conn.commit()

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════

threshold = 4.5
st.sidebar.title("⚙ System Control Panel")
st.sidebar.write(f"Logged in as: {st.session_state.role}")
st.sidebar.write(f"Threshold: {threshold} kW")

if st.sidebar.button("🚪 Logout"):
    st.session_state.role = None
    st.rerun()

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (5s)", value=True)

# ── Retrain (Admin only) ──────────────────────────────────────
if st.session_state.role == "admin":
    if st.sidebar.button("🔄 Retrain AI Model"):
        df = pd.read_sql_query(
            "SELECT hour, voltage, current, temperature, predicted_load FROM energy_log", conn
        )
        if len(df) > 10:
            X = df[['hour','voltage','current','temperature']]
            y = df['predicted_load']
            new_model = LinearRegression()
            new_model.fit(X, y)
            joblib.dump(new_model, "energy_model.pkl")
            st.sidebar.success("AI Model Retrained!")
        else:
            st.sidebar.warning("Not enough data to retrain.")

# ══════════════════════════════════════════════
# PAGE TITLE
# ══════════════════════════════════════════════

st.title("⚡ AI Smart Energy Management System")
st.subheader("Predictive Load Monitoring Dashboard")

# ══════════════════════════════════════════════
# LIVE SENSOR DATA FROM ESP32 VIA FIREBASE
# ══════════════════════════════════════════════

st.subheader("📡 Live ESP32 Sensor Data")

sensor_data = get_sensor_data()

if sensor_data:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⚡ Voltage",     f"{sensor_data.get('voltage', '--')} V")
    col2.metric("🔌 Current",     f"{sensor_data.get('current', '--')} A")
    col3.metric("💡 Power",       f"{sensor_data.get('power', '--')} W")
    col4.metric("🌡 Temperature", f"{sensor_data.get('temperature', '--')} °C")

    col5, col6 = st.columns(2)
    col5.metric("🤖 Predicted Load", f"{sensor_data.get('predicted_kw', '--')} kW")
    status = sensor_data.get('status', 'UNKNOWN')
    if status == "OVERLOAD":
        col6.error(f"⚠ Status: {status}")
    else:
        col6.success(f"✅ Status: {status}")

    st.caption(f"Last updated: {sensor_data.get('timestamp', '--')}")
else:
    st.warning("⏳ Waiting for ESP32 data... Make sure ESP32 is powered and connected to WiFi.")

st.divider()

# ══════════════════════════════════════════════
# LOAD AI MODEL
# ══════════════════════════════════════════════

model = joblib.load("energy_model.pkl")

# ══════════════════════════════════════════════
# MANUAL PREDICTION INPUTS
# ══════════════════════════════════════════════

st.subheader("🧠 Manual AI Prediction")

# Pre-fill with live ESP32 data if available
default_volt = float(sensor_data.get('voltage',     230.0)) if sensor_data else 230.0
default_curr = float(sensor_data.get('current',     2.0))   if sensor_data else 2.0
default_temp = float(sensor_data.get('temperature', 30.0))  if sensor_data else 30.0
default_hour = int(sensor_data.get('hour', datetime.now().hour)) if sensor_data else datetime.now().hour

hour    = st.slider("Select Hour (0-23)", 0, 23, default_hour)
voltage = st.number_input("Voltage (V)",      value=default_volt)
current = st.number_input("Current (A)",      value=default_curr)
temp    = st.number_input("Temperature (°C)", value=default_temp)

input_data = [[hour, voltage, current, temp]]
prediction = round(model.predict(input_data)[0], 2)

st.metric("Predicted Load (kW)", prediction)

# ══════════════════════════════════════════════
# OVERLOAD LOGIC
# ══════════════════════════════════════════════

if prediction > threshold:
    required_reduction = round(prediction - threshold, 2)
    st.error("⚠ OVERLOAD DETECTED")
    st.warning(f"Required Load Reduction: {required_reduction} kW")
    st.success(f"Adjusted Load: {threshold} kW")
    energy_saved = required_reduction * 1
    st.info(f"Estimated Energy Saved: {round(energy_saved, 2)} kWh")
else:
    st.success("✅ NORMAL LOAD - All Systems Stable")

# ══════════════════════════════════════════════
# SMART DB SAVE
# ══════════════════════════════════════════════

if "last_entry" not in st.session_state:
    st.session_state.last_entry = None

current_entry = (hour, voltage, current, temp, prediction)
if st.session_state.last_entry != current_entry:
    status = "OVERLOAD" if prediction > threshold else "NORMAL"
    cursor.execute("""
    INSERT INTO energy_log (timestamp, hour, voltage, current, temperature, predicted_load, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), hour, voltage, current, temp, prediction, status))
    conn.commit()
    st.session_state.last_entry = current_entry

# ══════════════════════════════════════════════
# RELAY CONTROL (sends commands to ESP32 via Firebase)
# ══════════════════════════════════════════════

st.subheader("🔌 Smart Relay Control")

relay_states = get_relay_states()

if prediction > threshold:
    st.error("🔴 Relay 1 (Decorative Load): OFF — Overload protection")
    st.error("🔴 Relay 2 (Extra Fans): OFF — Overload protection")
    st.success("🟢 Relay 3 (Essential Load): ON")
else:
    st.success("🟢 All Relays: ON — Normal load")

st.subheader("🖐 Manual Relay Control")
col_r1, col_r2, col_r3 = st.columns(3)

r1_state = relay_states.get('relay1', 0) == 1
r2_state = relay_states.get('relay2', 0) == 1
r3_state = relay_states.get('relay3', 1) == 1

with col_r1:
    st.write("**Relay 1**")
    if st.button("Turn ON"  if not r1_state else "Turn OFF", key="r1"):
        set_relay(1, not r1_state)
        st.rerun()
    st.write("🟢 ON" if r1_state else "🔴 OFF")

with col_r2:
    st.write("**Relay 2**")
    if st.button("Turn ON" if not r2_state else "Turn OFF", key="r2"):
        set_relay(2, not r2_state)
        st.rerun()
    st.write("🟢 ON" if r2_state else "🔴 OFF")

with col_r3:
    st.write("**Relay 3**")
    if st.button("Turn ON" if not r3_state else "Turn OFF", key="r3"):
        set_relay(3, not r3_state)
        st.rerun()
    st.write("🟢 ON" if r3_state else "🔴 OFF")

st.caption("💡 Manual controls send commands to ESP32 via Firebase in real-time")

# ══════════════════════════════════════════════
# ELECTRICITY BILL
# ══════════════════════════════════════════════

st.subheader("💰 Estimated Electricity Cost")
electricity_rate = 8
daily_energy     = prediction * 24
monthly_energy   = daily_energy * 30
monthly_bill     = monthly_energy * electricity_rate

st.write(f"Daily Consumption: {round(daily_energy, 2)} kWh")
st.write(f"Monthly Consumption: {round(monthly_energy, 2)} kWh")
st.success(f"Estimated Monthly Bill: ₹ {round(monthly_bill, 2)}")

# ══════════════════════════════════════════════
# LOAD CURVE GRAPHS
# ══════════════════════════════════════════════

data   = pd.read_csv("load_data.csv")
hours  = data["hour"]
actual = data["load"]

fig, ax = plt.subplots()
ax.plot(hours, actual, marker='o', label="Load")
ax.fill_between(hours, actual, threshold,
                where=(actual > threshold), color='red', alpha=0.3, label="Overload Zone")
ax.axhline(y=threshold, linestyle='--', label="Threshold")
ax.scatter(hour, prediction, color='green', s=120, label="Current Prediction")
ax.set_xlabel("Hour"); ax.set_ylabel("Load (kW)")
ax.set_title("Realistic 24-Hour Load Curve")
ax.legend()
st.pyplot(fig)

solar_generation = [0,0,0,0,0,0.5,1,2,3,4,5,5.5,6,6,5.5,5,4,3,2,1,0.5,0,0,0]
fig2, ax2 = plt.subplots()
ax2.plot(hours, actual, label="Load")
ax2.plot(hours, solar_generation, label="Solar Generation")
ax2.set_xlabel("Hour"); ax2.set_ylabel("Power (kW)")
ax2.set_title("Load vs Solar Generation")
ax2.legend()
st.pyplot(fig2)

# ══════════════════════════════════════════════
# DOWNLOAD REPORT
# ══════════════════════════════════════════════

report_data = f"""
AI Smart Energy Management Report
----------------------------------
Timestamp : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Hour      : {hour}
Voltage   : {voltage} V
Current   : {current} A
Temperature: {temp} °C
Predicted Load: {prediction} kW
Threshold : {threshold} kW
Status    : {"OVERLOAD" if prediction > threshold else "NORMAL"}
Est. Monthly Bill: Rs. {round(monthly_bill, 2)}

Live ESP32 Data:
  Voltage    : {sensor_data.get('voltage','N/A')} V
  Current    : {sensor_data.get('current','N/A')} A
  Power      : {sensor_data.get('power','N/A')} W
  Temperature: {sensor_data.get('temperature','N/A')} C
  Last Update: {sensor_data.get('timestamp','N/A')}
"""
st.download_button("📄 Download Report", report_data, file_name="energy_report.txt")

# ══════════════════════════════════════════════
# LOGGED HISTORY (Admin only)
# ══════════════════════════════════════════════

if st.session_state.role == "admin":
    st.subheader("📊 Logged Prediction History")
    data_log = pd.read_sql_query(
        "SELECT * FROM energy_log ORDER BY id DESC LIMIT 10", conn
    )
    st.dataframe(data_log)

# ══════════════════════════════════════════════
# AUTO REFRESH
# ══════════════════════════════════════════════

if auto_refresh:
    time.sleep(5)
    st.rerun()
