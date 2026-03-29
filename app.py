import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

import firebase_admin
from firebase_admin import credentials, db

st_autorefresh(interval=3000, key="refresh")
st.set_page_config(page_title="AI Energy SCADA", layout="wide")

# 🎨 STYLE
st.markdown("""
<style>
[data-testid="stMetricValue"] {color:#00FF00 !important;font-weight:bold;}
[data-testid="stMetricLabel"] {color:#FFFFFF !important;}
.stMetric {background:#1c1f26;padding:15px;border-radius:10px;}
body {background-color:#0e1117;}
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

# ---------------- FIREBASE ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- DATA ----------------
sensor = ref.child("sensor_data").get()
relay = ref.child("relay_control").get()

if sensor:
    voltage = float(sensor.get("voltage", 0))
    current = float(sensor.get("current", 0))
    temp = float(sensor.get("temperature", 0))
    power_watt = float(sensor.get("power", 0))
else:
    voltage, current, temp, power_watt = 0, 0, 0, 0

if relay:
    r1 = bool(relay.get("relay1", 0))
    r2 = bool(relay.get("relay2", 0))
    r3 = bool(relay.get("relay3", 0))
else:
    r1 = r2 = r3 = False

# ---------------- RELAY LOAD ----------------
relay_load = (2 if r1 else 0) + (1.5 if r2 else 0) + (1 if r3 else 0)

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# 🔥 SLIDER AUTO BASED ON RELAY LOAD
sim = st.sidebar.slider("⚡ Simulated Load", 0.0, 7.0, float(relay_load))

# 🔥 TOTAL AI LOAD
ai_total = sim

threshold = 4.5

# ================= AI LOGIC (FIXED FINAL) =================
new_r1, new_r2, new_r3 = r1, r2, r3
ai_active = False

if sim > 4.5:
    ai_active = True

    if 4.51 <= sim <= 5.5:
        new_r3 = False
    elif 5.51 <= sim <= 6:
        new_r2 = False
    elif 6.01 <= sim <= 6.5:
        new_r1 = False

# 🔥 IMPORTANT: update ONLY if changed
if (new_r1 != r1) or (new_r2 != r2) or (new_r3 != r3):
    ref.child("relay_control").update({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    # SENSOR ONLY
    st.metric("Live Power (W)", round(power_watt,2))

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

    # 🔥 OVERLOAD FIXED
    if sim > 4.5:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    # 🔥 SAME SLIDER HERE
    sim2 = st.slider("⚡ Simulated Load", 0.0, 7.0, float(relay_load))

    if ai_active:
        st.warning("⚠ AI Load Shedding Active")

    new_r1 = st.toggle("Relay 1 (2kW)", r1)
    new_r2 = st.toggle("Relay 2 (1.5kW)", r2)
    new_r3 = st.toggle("Relay 3 (1kW)", r3)

    if new_r1 != r1 or new_r2 != r2 or new_r3 != r3:
        ref.child("relay_control").set({
            "relay1": int(new_r1),
            "relay2": int(new_r2),
            "relay3": int(new_r3)
        })
        st.rerun()

# ================= ANALYTICS =================
elif menu == "📊 Analytics":
    st.header("Hourly Energy")

# ================= REPORT =================
elif menu == "📄 Reports":
    st.header("Reports")
