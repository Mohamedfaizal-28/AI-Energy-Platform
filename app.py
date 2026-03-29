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

# PAGE
st.set_page_config(page_title="AI Energy SCADA", layout="wide")

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

# ---------------- FIREBASE ----------------
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

# ---------------- RELAY LOADS ----------------
R1_LOAD = 2.0
R2_LOAD = 1.5
R3_LOAD = 1.0

threshold = 4.5

# ---------------- DATA ----------------
sensor = ref.child("sensor_data").get()
relay = ref.child("relay_control").get()

power_watt = float(sensor.get("power", 0)) if sensor else 0

r1 = bool(relay.get("relay1", 0)) if relay else False
r2 = bool(relay.get("relay2", 0)) if relay else False
r3 = bool(relay.get("relay3", 0)) if relay else False

# ---------------- RELAY TOTAL ----------------
relay_total = (
    (R1_LOAD if r1 else 0) +
    (R2_LOAD if r2 else 0) +
    (R3_LOAD if r3 else 0)
)

# ---------------- SLIDER (AUTO SYNC) ----------------
if "slider_val" not in st.session_state:
    st.session_state.slider_val = relay_total

# Sync slider with relay
st.session_state.slider_val = relay_total

slider = st.sidebar.slider("⚡ Total Load (kW)", 0.0, 7.0, st.session_state.slider_val)

ai_power = slider

# ---------------- ENERGY ----------------
interval = 3
hour = now.hour

power_kw = power_watt / 1000
energy_inc = power_kw * (interval / 3600)
st.session_state.energy_log[hour] += energy_inc

today_energy = sum(st.session_state.energy_log.values())
today_cost = today_energy * 8

# ================= DASHBOARD =================
st.title("⚡ AI Energy SCADA Dashboard")

st.metric("Live Power (W)", round(power_watt, 2))
st.metric("Today Energy (kWh)", round(today_energy, 3))
st.metric("Cost ₹", round(today_cost, 2))

# ---------------- AI LOGIC ----------------
if ai_power > threshold:

    if 4.5 < ai_power <= 5.5:
        ref.child("relay_control/relay3").set(0)
        st.warning("⚠ Relay 3 OFF (1 kW shed)")
        r3 = False

    elif 5.5 < ai_power <= 6.0:
        ref.child("relay_control/relay2").set(0)
        st.warning("⚠ Relay 2 OFF (1.5 kW shed)")
        r2 = False

    elif 6.0 < ai_power <= 6.5:
        ref.child("relay_control/relay1").set(0)
        st.warning("⚠ Relay 1 OFF (2 kW shed)")
        r1 = False

# ---------------- UPDATE SLIDER AFTER AI ----------------
relay_total_after = (
    (R1_LOAD if r1 else 0) +
    (R2_LOAD if r2 else 0) +
    (R3_LOAD if r3 else 0)
)

st.session_state.slider_val = relay_total_after

# ---------------- STATUS ----------------
if ai_power > threshold:
    st.error("🔴 OVERLOAD")
else:
    st.success("🟢 NORMAL")
