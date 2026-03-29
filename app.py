import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

# AUTO REFRESH
st_autorefresh(interval=2000, key="refresh")

# PAGE CONFIG
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

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- TIME ----------------
india = pytz.timezone('Asia/Kolkata')
now = datetime.now(india)

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
body {background-color:#0b0f1a;color:#e6edf3;}
.card {
    background:#111827;
    padding:15px;
    border-radius:12px;
    margin:5px;
}
.blink {animation: blink 1s infinite;}
@keyframes blink {50% {opacity:0.3;}}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control"
])

st.sidebar.write(f"User: {st.session_state.role}")

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

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
    r1 = bool(relay_fb.get("relay1", 0))
    r2 = bool(relay_fb.get("relay2", 0))
    r3 = bool(relay_fb.get("relay3", 0))
else:
    r1 = r2 = r3 = False

# ---------------- SLIDER (FIXED) ----------------
if "slider" not in st.session_state:
    st.session_state["slider"] = 0.0

sim = st.sidebar.slider("⚡ Simulated Load", 0.0, 7.5, key="slider")

total_power = power + sim

# ---------------- RELAY LOAD VALUES ----------------
relay_load = {
    "r1": 2.0,
    "r2": 1.5,
    "r3": 1.0
}

cut_load = 0

# ================= AI LOAD SHEDDING =================
if total_power > 4.5:

    if 4.51 <= total_power <= 5.5:
        r3 = False
        cut_load = relay_load["r3"]

    elif 5.51 <= total_power <= 6:
        r2 = False
        cut_load = relay_load["r2"]

    elif 6.01 <= total_power <= 6.5:
        r1 = False
        cut_load = relay_load["r1"]

    elif 6.51 <= total_power <= 7.5:
        r1 = False
        r3 = False
        cut_load = relay_load["r1"] + relay_load["r3"]

# FINAL POWER AFTER AI
final_power = max(0, total_power - cut_load)

# SAFE UPDATE (NO CRASH)
if abs(st.session_state["slider"] - final_power) > 0.01:
    st.session_state["slider"] = final_power

# ---------------- WRITE TO FIREBASE ----------------
ref.child("relay_control").set({
    "relay1": int(r1),
    "relay2": int(r2),
    "relay3": int(r3)
})

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"<div class='card'>Voltage<br><b>{voltage} V</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'>Current<br><b>{current} A</b></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'>Temperature<br><b>{temp} °C</b></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='card'>Live Power<br><b>{round(final_power,2)} kW</b></div>", unsafe_allow_html=True)

    if final_power > 4.5:
        st.markdown("<div class='card blink' style='color:red'>🔴 OVERLOAD</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='card' style='color:lime'>🟢 NORMAL</div>", unsafe_allow_html=True)

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control (Manual Override)")

    new_r1 = st.checkbox("Relay 1", r1)
    new_r2 = st.checkbox("Relay 2", r2)
    new_r3 = st.checkbox("Relay 3", r3)

    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    st.success("Relay updated to Firebase")
