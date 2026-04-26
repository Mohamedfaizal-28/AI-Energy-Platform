import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

import csv
import time
import pickle
import numpy as np

def save_load_data(load, r1, r2, r3):
    from datetime import datetime
    current_time = datetime.now().strftime("%H:%M:%S")

    with open("load_data.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([current_time, load, int(r1), int(r2), int(r3)])

if "last_saved" not in st.session_state:
    st.session_state.last_saved = 0
    
st_autorefresh(interval=1000, key="refresh")
# PAGE
st.set_page_config(page_title="AI Energy SCADA", layout="wide")

# 🎨 STYLE
st.markdown("""
<style>
body {background-color:#0e1117;color:white;}
.stMetric {background:#1c1f26;padding:15px;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
def check_login(user, pwd):
    return (user == "Admin" and pwd == "1234") or (user == "User" and pwd == "1234")

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(user, pwd):
            st.session_state.login = True
            st.session_state.role = user
            st.rerun()
        else:
            st.error("Invalid Login")

    st.stop()

# ---------------- TIME ----------------
india = pytz.timezone('Asia/Kolkata')
now = datetime.now(india)
today = now.strftime("%Y-%m-%d")
month = now.strftime("%Y-%m")
current_hour = now.hour
# ---------------- FIREBASE ----------------
if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')
# 🔥 LOAD AI MODEL
model = pickle.load(open("energy_model.pkl", "rb"))
# ---------------- SESSION ----------------
if "date" not in st.session_state:
    st.session_state.date = today

if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

if "daily_energy" not in st.session_state:
    st.session_state.daily_energy = {}

if "monthly_energy" not in st.session_state:
    st.session_state.monthly_energy = {}

# 🔁 DAILY RESET
if st.session_state.date != today:
    yesterday_energy = sum(st.session_state.energy_log.values())
    st.session_state.daily_energy[st.session_state.date] = yesterday_energy
    st.session_state.monthly_energy[month] = st.session_state.monthly_energy.get(month, 0) + yesterday_energy
    st.session_state.energy_log = {i: 0 for i in range(24)}
    st.session_state.date = today

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

st.sidebar.write(f"User: {st.session_state.role}")
if "pending_request" not in st.session_state:
    st.session_state.pending_request = None

if "last_warning" not in st.session_state:
    st.session_state.last_warning = False
    
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

threshold = 3.6  # kW

# 🔥 ADD BELOW threshold
if "voltage_limit" not in st.session_state:
    st.session_state.voltage_limit = 230

voltage_limit = st.session_state.voltage_limit

# ---------------- FIREBASE DATA ----------------
sensor = ref.child("sensor_data").get()
relay = ref.child("relay_control").get()
# 🔥 FORCE INITIAL SAFE STATE
if relay is None:
    ref.child("relay_control").set({
        "relay1": 0,
        "relay2": 0,
        "relay3": 0
    })
    st.rerun()
    
if sensor:
    voltage = float(sensor.get("voltage") or 0)
    current = float(sensor.get("current") or 0)
    temp = float(sensor.get("temperature") or 0)
    power = float(sensor.get("power") or 0)
    # 🔥 REMOVE NOISE
    if power < 10:
        power = 0
    energy = float(sensor.get("energy") or 0)
else:
    voltage, current, temp, power, energy = 0, 0, 0, 0, 0

if relay:
    r1 = bool(relay.get("relay1", 0))
    r2 = bool(relay.get("relay2", 0))
    r3 = bool(relay.get("relay3", 0))
else:
    r1 = r2 = r3 = False

# ---------------- RELAY LOAD ----------------
relay_total = (
    (2.0 if r1 else 0) +
    (1.5 if r2 else 0) +
    (1.0 if r3 else 0)
)

relay_total = float(max(0.0, min(relay_total, 7.0)))

total_power = relay_total

# 🔥 AI INPUT
input_data = np.array([[voltage, current, temp, current_hour]])

# 🔥 FIX 2 (ADD HERE)
if voltage == 0 or current < 0.01:
    predicted_load = total_power * 1000  # fallback when sensor fails
else:
    predicted_load = max(power * 1.2, model.predict(input_data)[0] + 20)

# -------- SAVE DATA EVERY 5 SECONDS --------
if "prev_load" not in st.session_state:
    st.session_state.prev_load = None

if time.time() - st.session_state.last_saved > 5:
    if st.session_state.prev_load != total_power:
        save_load_data(total_power, r1, r2, r3)
        st.session_state.prev_load = total_power
        st.session_state.last_saved = time.time()
# ---------------- ENERGY ----------------
interval = 3
hour = now.hour

power_kw = (power or 0) / 1000
energy_inc = power_kw * (interval / 3600)
st.session_state.energy_log[hour] += energy_inc

today_energy = sum(st.session_state.energy_log.values())
today_cost = today_energy * 8

monthly_energy = st.session_state.monthly_energy.get(month, 0)
monthly_cost = monthly_energy * 8

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    # 🎨 Dashboard Text Visibility Fix
    st.markdown("""
    <style>
    [data-testid="stMetricLabel"] {
        color: white !important;
        font-weight: bold;
    }
    [data-testid="stMetricValue"] {
        color: white !important;
    }
    [data-testid="stMetricDelta"] {
        color: white !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Live Power (W)", round(power, 2))
    st.metric("Energy (kWh)", round(energy, 3))

    st.metric("Total Energy (kWh)", round(energy, 3))
    st.metric("Total Cost ₹", round(energy * 8, 2))

    st.metric("Total Load (kW)", round(total_power, 2))
    st.metric("Predicted Load (W)", round(predicted_load, 2))
    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

    if total_power > threshold:
        st.error("🔴 OVERLOAD (Voltage Limit Exceeded)")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.subheader("⚡ Load Limit Control")

    load_limit = st.slider(
        "Set Maximum Load (kW)",
        1.0, 7.0, 3.5
    )

    st.session_state.voltage_limit = voltage_limit

    st.header("Relay Control")

    new_r1 = st.toggle("Relay 1", value=r1)
    new_r2 = st.toggle("Relay 2", value=r2)
    new_r3 = st.toggle("Relay 3", value=r3)

    # 🔥 VOLTAGE BASED CONTROL
    if total_power > load_limit:

        st.warning("⚠ Voltage exceeded limit - Turning OFF priority load")

        if new_r3:
            new_r3 = False
        elif new_r2:
            new_r2 = False
        elif new_r1:
            new_r1 = False

    # 🔥 UPDATE FIREBASE
    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    st.write("Final Relay State:")
    st.write({
        "Relay1": new_r1,
        "Relay2": new_r2,
        "Relay3": new_r3
    })

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Actual vs Predicted Load")

    if "history" not in st.session_state:
        st.session_state.history = []

    st.session_state.history.append({
        "Actual": power,
        "Predicted": predicted_load
    })
    
    if len(st.session_state.history) > 50:
        st.session_state.history.pop(0)

    df = pd.DataFrame(st.session_state.history)

    st.line_chart(df)

# ================= REPORT =================
elif menu == "📄 Reports":

    st.header("Reports")

    st.write("Daily Energy:", st.session_state.daily_energy)
    st.write("Monthly Energy:", st.session_state.monthly_energy)

    report = f"""
Date: {today}
Today Energy: {today_energy}
Monthly Energy: {monthly_energy}
Cost: {today_cost}
"""

    st.download_button("Download Report", report)
