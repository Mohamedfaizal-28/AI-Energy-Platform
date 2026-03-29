import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt

# 🔥 AUTO REFRESH
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="refresh")

# 🔥 PAGE CONFIG
st.set_page_config(page_title="AI Energy System", page_icon="⚡", layout="wide")

# 🔥 UI
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
}
.stMetric {
    background: rgba(255,255,255,0.05);
    padding: 15px;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- LOGIN ----------------
def check_login(username, password):
    return username == "Admin" and password == "1234"

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.title("🔐 Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(user, pwd):
            st.session_state.role = "Admin"
            st.rerun()
        else:
            st.error("Invalid")

    st.stop()

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# ---------------- FIREBASE DATA ----------------
data = ref.child("sensor_data").get()

if data:
    voltage = float(data.get("voltage", 230))
    current = float(data.get("current", 0.5))
    temp = float(data.get("temperature", 30))
else:
    voltage, current, temp = 230, 0.5, 30

# ---------------- LOAD CALCULATION ----------------
real_power = round((voltage * current) / 1000, 2)  # kW

# ---------------- RELAY LOAD (FIXED) ----------------
relay_loads = {
    "relay1": 2.0,
    "relay2": 1.5,
    "relay3": 1.0
}

# ---------------- ENERGY STORAGE ----------------
if "energy" not in st.session_state:
    st.session_state.energy = 0

# Add consumption every refresh (~5 sec)
st.session_state.energy += real_power * (5/3600)

# ========================= DASHBOARD =========================
if menu == "🏠 Dashboard":

    st.title("⚡ Smart Energy Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Real Load (kW)", real_power)

    if real_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ========================= RELAY CONTROL =========================
elif menu == "🔌 Relay Control":

    st.header("Smart Relay Control")

    # Manual variation slider (simulate load change)
    variation = st.slider("Adjust Load (+/-)", -2.0, 2.0, 0.0)

    adjusted_load = real_power + variation

    st.metric("Adjusted Load (kW)", round(adjusted_load, 2))

    # Smart optimization
    relay_state = {
        "relay1": True,
        "relay2": True,
        "relay3": True
    }

    if adjusted_load > 6.5:
        relay_state["relay1"] = False
    elif adjusted_load > 5.5:
        relay_state["relay2"] = False
    elif adjusted_load > 4.5:
        relay_state["relay3"] = False

    # Display relay status
    for r, state in relay_state.items():
        if state:
            st.success(f"{r} ON")
        else:
            st.error(f"{r} OFF")

    # Send to Firebase
    ref.child("relay_control").set({
        "relay1": int(relay_state["relay1"]),
        "relay2": int(relay_state["relay2"]),
        "relay3": int(relay_state["relay3"])
    })

# ========================= ANALYTICS =========================
elif menu == "📊 Analytics":

    st.header("Energy Analytics")

    data = pd.read_csv("load_data.csv")

    fig, ax = plt.subplots()
    ax.plot(data["hour"], data["load"], linewidth=3)
    ax.axhline(y=threshold, linestyle='--')
    ax.scatter(12, real_power, s=150)

    ax.set_facecolor("#111")
    fig.patch.set_facecolor("#111")

    st.pyplot(fig)

# ========================= REPORT =========================
elif menu == "📄 Reports":

    st.header("Energy Report")

    energy_used = round(st.session_state.energy, 3)

    electricity_rate = 8
    cost = energy_used * electricity_rate

    st.metric("Total Energy Used (kWh)", energy_used)
    st.metric("Estimated Cost (₹)", round(cost, 2))

    report = f"""
Energy Report
-------------
Voltage: {voltage}
Current: {current}
Temperature: {temp}
Load: {real_power} kW
Energy Used: {energy_used} kWh
Cost: ₹{round(cost,2)}
"""

    st.download_button("Download Report", report)
