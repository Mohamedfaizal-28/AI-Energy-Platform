import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

# AUTO REFRESH
st_autorefresh(interval=3000, key="refresh")

st.set_page_config(page_title="AI Energy SCADA", layout="wide")

# ---------------- TIME FIX (INDIA TIME) ----------------
india = pytz.timezone('Asia/Kolkata')
now = datetime.now(india)
current_hour = now.hour
today = now.strftime("%Y-%m-%d")

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- SESSION ----------------
if "date" not in st.session_state:
    st.session_state.date = today

if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

if "history" not in st.session_state:
    st.session_state.history = {}

# 🔁 RESET DAILY
if st.session_state.date != today:
    st.session_state.history[st.session_state.date] = st.session_state.energy_log
    st.session_state.energy_log = {i: 0 for i in range(24)}
    st.session_state.date = today

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# ---------------- FIREBASE READ ----------------
sensor = ref.child("sensor_data").get()
relay_fb = ref.child("relay_control").get()

if sensor:
    voltage = float(sensor.get("voltage", 0))
    current = float(sensor.get("current", 0))
    temp = float(sensor.get("temperature", 0))
    power = float(sensor.get("power", 0))
else:
    voltage, current, temp, power = 0, 0, 0, 0

if relay_fb:
    relay1 = bool(relay_fb.get("relay1", 0))
    relay2 = bool(relay_fb.get("relay2", 0))
    relay3 = bool(relay_fb.get("relay3", 0))
else:
    relay1 = relay2 = relay3 = False

# ---------------- DEMO OVERLOAD SLIDER ----------------
simulation = st.sidebar.slider("⚡ Simulate Load (Demo)", 0.0, 7.0, 0.0)

total_power = power + simulation

# ---------------- ENERGY ----------------
interval = 3
energy_increment = total_power * (interval / 3600)

st.session_state.energy_log[current_hour] += energy_increment

total_energy = sum(st.session_state.energy_log.values())
cost = total_energy * 8

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Live Power (kW)", round(total_power,2))

    col4, col5 = st.columns(2)
    col4.metric("Energy Today (kWh)", round(total_energy,3))
    col5.metric("Cost Today (₹)", round(cost,2))

    st.info(f"🕒 Current Time: {now.strftime('%H:%M:%S')}")

    # AI ALERT
    if total_power > threshold:
        st.error("🔴 OVERLOAD PREDICTED")
    else:
        st.success("🟢 SYSTEM NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Smart Relay Control")

    new_r1 = st.toggle("Relay 1", value=relay1)
    new_r2 = st.toggle("Relay 2", value=relay2)
    new_r3 = st.toggle("Relay 3", value=relay3)

    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    # AI LOAD SHEDDING
    if total_power > threshold:
        st.warning("⚠ AI is optimizing load...")

        if total_power <= 5.5:
            ref.child("relay_control/relay3").set(0)
        elif total_power <= 6:
            ref.child("relay_control/relay2").set(0)
        else:
            ref.child("relay_control/relay1").set(0)

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Today's Energy Usage")

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))

# ================= REPORT =================
elif menu == "📄 Reports":

    st.header("Energy Report")

    st.subheader("Today")
    st.write(st.session_state.energy_log)

    st.subheader("History")
    st.write(st.session_state.history)

    report = f"""
Date: {today}
Energy: {total_energy} kWh
Cost: ₹{cost}
"""

    st.download_button("Download Report", report)
