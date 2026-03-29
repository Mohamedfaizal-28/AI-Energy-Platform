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

# 🎨 STYLE
st.markdown("""
<style>
body {background-color:#0e1117;color:white;}
.stMetric {background:#1c1f26;padding:15px;border-radius:10px;}
.stMetric label {color:#00ff88 !important;}
.stMetric div {color:#00ff88 !important;font-size:22px !important;}
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

# ---------------- FIREBASE ----------------
if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- SESSION ----------------
if "sim_load" not in st.session_state:
    st.session_state.sim_load = 0.0

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

st.sidebar.write(f"User: {st.session_state.role}")

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

threshold = 4.5

# ---------------- DATA ----------------
sensor = ref.child("sensor_data").get()
relay = ref.child("relay_control").get()

if sensor:
    voltage = float(sensor.get("voltage", 0))
    current = float(sensor.get("current", 0))
    temp = float(sensor.get("temperature", 0))
    power = float(sensor.get("power", 0))
else:
    voltage, current, temp, power = 0, 0, 0, 0

if relay:
    r1 = bool(relay.get("relay1", 0))
    r2 = bool(relay.get("relay2", 0))
    r3 = bool(relay.get("relay3", 0))
else:
    r1 = r2 = r3 = False

# ---------------- SLIDER ----------------
sim = st.sidebar.slider(
    "⚡ Simulated Load",
    0.0, 7.0,
    st.session_state.sim_load
)

total_power = power + sim

# ---------------- 🔥 GLOBAL AI LOGIC (FIXED) ----------------
if total_power > threshold:

    if total_power <= 5.5:
        ref.child("relay_control/relay3").set(0)
        r3 = False
    elif total_power <= 6:
        ref.child("relay_control/relay2").set(0)
        r2 = False
    else:
        ref.child("relay_control/relay1").set(0)
        r1 = False

    # 🔥 Update slider AFTER relay OFF (NO FIXED LOAD USED)
    st.session_state.sim_load = max(0.0, threshold - power)
    st.rerun()

# ---------------- DASHBOARD ----------------
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Live Power (kW)", round(total_power,2))

    if total_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ---------------- RELAY ----------------
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    new_r1 = st.toggle("Relay 1", r1)
    new_r2 = st.toggle("Relay 2", r2)
    new_r3 = st.toggle("Relay 3", r3)

    # SAVE
    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    # 🔥 UPDATE SLIDER WHEN USER MANUALLY CHANGES RELAY
    st.session_state.sim_load = max(0.0, threshold - power)

# ---------------- ANALYTICS ----------------
elif menu == "📊 Analytics":

    st.header("Analytics")
    st.write("Coming Soon...")

# ---------------- REPORT ----------------
elif menu == "📄 Reports":

    st.header("Reports")
    st.write("Coming Soon...")
