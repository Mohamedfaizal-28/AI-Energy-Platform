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

# 🎨 SCADA STYLE
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        color: #00FF00 !important; /* Bright Green Numbers */
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #FFFFFF !important; /* Pure White Labels */
    }
    .stMetric {
        background:#1c1f26; 
        padding:15px; 
        border-radius:10px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)


# ---------------- LOGIN SYSTEM ----------------
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

if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

threshold = 4.5

# ---------------- FIREBASE ----------------
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

# 🔥 DEMO SLIDER
sim = st.sidebar.slider("⚡ Simulated Load", 0.0, 7.0, 0.0)
total_power = power + sim

# ---------------- ENERGY ----------------
interval = 3
hour = now.hour

energy_inc = total_power * (interval/3600)
st.session_state.energy_log[hour] += energy_inc

today_energy = sum(st.session_state.energy_log.values())
today_cost = today_energy * 8

monthly_energy = st.session_state.monthly_energy.get(month, 0)
monthly_cost = monthly_energy * 8

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy Dashboard")

    # We use a dummy delta " " to force the styling to green without showing a number
    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V", delta="Normal", delta_color="normal")
    col2.metric("Current", f"{current} A", delta="Live", delta_color="normal")
    col3.metric("Temperature", f"{temp} °C", delta="Stable", delta_color="normal")

    st.metric("Live Power (kW)", round(total_power,2), delta="Active", delta_color="normal")

    col4, col5 = st.columns(2)
    col4.metric("Today Energy", round(today_energy,3), delta="⚡", delta_color="normal")
    col5.metric("Today Cost ₹", round(today_cost,2), delta="₹", delta_color="normal")

    col6, col7 = st.columns(2)
    col6.metric("Monthly Energy", round(monthly_energy,3), delta="OK", delta_color="normal")
    col7.metric("Monthly Cost ₹", round(monthly_cost,2), delta="OK", delta_color="normal")

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

    if total_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")


# ================= RELAY =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    new_r1 = st.toggle("Relay 1", r1)
    new_r2 = st.toggle("Relay 2", r2)
    new_r3 = st.toggle("Relay 3", r3)

    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    # AI LOAD SHEDDING
    if total_power > threshold:
        st.warning("⚠ AI Optimizing Load")

        if total_power <= 5.5:
            ref.child("relay_control/relay3").set(0)
        elif total_power <= 6:
            ref.child("relay_control/relay2").set(0)
        else:
            ref.child("relay_control/relay1").set(0)

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
