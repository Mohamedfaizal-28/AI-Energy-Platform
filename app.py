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

threshold = 4.5  # kW

# ---------------- FIREBASE DATA ----------------
sensor = ref.child("sensor_data").get()
relay = ref.child("relay_control").get()

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

# ---------------- SLIDER ----------------
# SAFE INITIAL VALUE
if "sim" not in st.session_state:
    st.session_state.sim = float(relay_total)

# ENSURE VALUE IS ALWAYS VALID
st.session_state.sim = max(0.0, min(float(st.session_state.sim), 7.0))

# SLIDER
sim = st.sidebar.slider(
    "⚡ Total Load (kW)",
    min_value=0.0,
    max_value=7.0,
    value=st.session_state.sim,
    step=0.1
)

# UPDATE SESSION
st.session_state.sim = sim

total_power = sim

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
/* Metric label */
[data-testid="stMetricLabel"] {
    color: white !important;
    font-weight: bold;
}

/* Metric value */
[data-testid="stMetricValue"] {
    color: white !important;
}

/* Metric delta (if any) */
[data-testid="stMetricDelta"] {
    color: white !important;
}

/* General text */
h1, h2, h3, h4, h5, h6, p {
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

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

    if total_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    new_r1 = st.toggle("Relay 1", r1)
    new_r2 = st.toggle("Relay 2", r2)
    new_r3 = st.toggle("Relay 3", r3)

    # 🔥 AI CONTROL (FIXED)
    if total_power > threshold:
        st.warning("⚠ AI Optimizing Load")

        if total_power > 6.0:
            new_r1 = False
        elif total_power > 5.5:
            new_r2 = False
        elif total_power > 4.5:
            new_r3 = False

    # UPDATE FIREBASE
    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    # AUTO UPDATE SLIDER
    relay_total = (
        (2.0 if new_r1 else 0) +
        (1.5 if new_r2 else 0) +
        (1.0 if new_r3 else 0)
    )

    st.session_state.sim = relay_total

    st.write("Final Relay State (AI Controlled):")
    st.write({
        "Relay1": new_r1,
        "Relay2": new_r2,
        "Relay3": new_r3
    })

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
