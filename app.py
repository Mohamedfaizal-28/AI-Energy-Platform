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
if "is_speaking" not in st.session_state:
    st.session_state.is_speaking = False
    
# AUTO REFRESH
st_autorefresh(interval=2000, key="refresh")

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

threshold = 3.0  # kW

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
    
if sensor:
    voltage = float(sensor.get("voltage") or 0)
    current = float(sensor.get("current") or 0)
    temp = float(sensor.get("temperature") or 0)
    power = float(sensor.get("power") or 0)
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
    predicted_load = max(0, model.predict(input_data)[0])

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

    col4, col5 = st.columns(2)
    col4.metric("Today Energy", round(today_energy, 3))
    col5.metric("Today Cost ₹", round(today_cost, 2))

    col6, col7 = st.columns(2)
    col6.metric("Monthly Energy", round(monthly_energy, 3))
    col7.metric("Monthly Cost ₹", round(monthly_cost, 2))

    st.metric("Total Load (kW)", round(total_power, 2))
    st.metric("Predicted Load (W)", round(predicted_load, 2))
    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

    if total_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    # 🔥 INIT SESSION RELAY STATE (VERY IMPORTANT)
    if "relay_state" not in st.session_state:
        st.session_state.relay_state = {
            "relay1": r1,
            "relay2": r2,
            "relay3": r3
        }

    state = st.session_state.relay_state

    # 🔥 TOGGLES (USE SESSION STATE)
    new_r1 = st.toggle("Relay 1", value=state["relay1"])
    new_r2 = st.toggle("Relay 2", value=state["relay2"])
    new_r3 = st.toggle("Relay 3", value=state["relay3"])

    # 🔥 COUNT CURRENT ACTIVE LOADS
    current_on = sum(state.values())

    # 🔥 DETECT REQUEST
    requested = None
    if new_r1 and not state["relay1"]:
        requested = "relay1"
    elif new_r2 and not state["relay2"]:
        requested = "relay2"
    elif new_r3 and not state["relay3"]:
        requested = "relay3"

    message = ""

    # 🔥 BLOCK LOGIC
    if requested and current_on >= 2:

        message = "⚠ Turning this load may cause overload. Please turn OFF any load to prevent overload."

        st.session_state.pending_request = requested

        # cancel action
        new_r1 = state["relay1"]
        new_r2 = state["relay2"]
        new_r3 = state["relay3"]
        
        st.rerun()

    # 🔥 APPLY USER ACTION (ONLY IF SAFE)
    else:
        # Apply ONLY real user changes
        if new_r1 != state["relay1"]:
            state["relay1"] = new_r1
    
        if new_r2 != state["relay2"]:
            state["relay2"] = new_r2
    
        if new_r3 != state["relay3"]:
            state["relay3"] = new_r3

    # 🔥 AUTO TURN ON PENDING (CORRECT LOGIC)
    if st.session_state.pending_request:

        req = st.session_state.pending_request
    
        current_on = sum(state.values())
    
        # ONLY trigger when user turned OFF exactly one load
        if current_on == 1 and not state[req]:
    
            state[req] = True
    
            message = "✅ Pending load turned ON automatically."
    
            st.session_state.pending_request = None

    # 🔥 UPDATE FIREBASE (ONLY FINAL STATE)
    ref.child("relay_control").set({
        "relay1": int(state["relay1"]),
        "relay2": int(state["relay2"]),
        "relay3": int(state["relay3"])
    })

    # 🔥 SHOW MESSAGE
    st.write("### Status:")
    if message:
        st.warning(message)
    else:
        st.success("System running normally")

    st.write(state)
# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Hourly Energy")

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))

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
