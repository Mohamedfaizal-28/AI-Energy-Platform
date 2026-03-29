import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

# AUTO REFRESH (Every 3 seconds)
st_autorefresh(interval=3000, key="refresh")

# PAGE
st.set_page_config(page_title="AI Energy SCADA", layout="wide")

# 🎨 SCADA STYLE - FORCED GREEN METRICS
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        color: #00FF00 !important; /* Neon Green */
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #FFFFFF !important; /* White Labels */
    }
    .stMetric {
        background:#1c1f26; 
        padding:15px; 
        border-radius:10px;
        border: 1px solid #333;
    }
    body { background-color: #0e1117; }
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

# ---------------- DATA FETCHING ----------------
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

# ---------------- GLOBAL CONTROL LOGIC ----------------
st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", ["🏠 Dashboard", "🔌 Relay Control", "📊 Analytics", "📄 Reports"])

# 1. Calculate weighted load from relays
calc_load = (int(r1) * 2.0) + (int(r2) * 1.5) + (int(r3) * 1.0)

# 2. Sidebar Slider (Auto-adjusts based on calc_load)
sim = st.sidebar.slider("⚡ Simulated Load", 0.0, 7.0, float(calc_load))
total_power = power + sim
threshold = 4.5

# 🔥 GLOBAL AI LOAD SHEDDING (Works on all pages)
ai_active = False
if total_power > threshold:
    ai_active = True
    
    # Specific logic bands
    if 4.5 < total_power <= 5.5:
        r3 = False
    elif 5.5 < total_power <= 6.0:
        r2 = False
    elif 6.0 < total_power <= 6.5:
        r1 = False
    elif 6.5 < total_power <= 7.0:
        r1 = False
        r3 = False

    # Sync AI changes back to Firebase immediately
    ref.child("relay_control").update({
        "relay1": int(r1),
        "relay2": int(r2),
        "relay3": int(r3)
    })

st.sidebar.write(f"User: {st.session_state.role}")
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

# ---------------- ENERGY CALC (FIXED WITH FIREBASE) ----------------
interval = 3
hour = now.hour
energy_inc = total_power * (interval / 3600)

# 🔥 STORE HOURLY ENERGY IN FIREBASE
hour_ref = ref.child("energy").child(today).child(str(hour))
prev_energy = hour_ref.get() or 0
hour_ref.set(prev_energy + energy_inc)

# 🔥 GET TODAY ENERGY
day_data = ref.child("energy").child(today).get()
if day_data:
    today_energy = sum(day_data.values())
else:
    today_energy = 0

today_cost = today_energy * 8

# 🔥 MONTHLY ENERGY STORE
month_ref = ref.child("monthly").child(month)
prev_month_energy = month_ref.get() or 0

# Update monthly continuously
month_ref.set(prev_month_energy + energy_inc)

monthly_energy = month_ref.get() or 0
monthly_cost = monthly_energy * 8

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":
    st.title("⚡ AI Energy Dashboard")

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

    # Overload Status (only triggers if over 4.5)
    if total_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":
    st.header("Relay Control")

    if ai_active:
        st.warning("⚠ AI Load Shedding Active - Some relays forced OFF")

    # Display Toggles (Updating these will trigger a refresh and global AI logic)
    new_r1 = st.toggle("Relay 1 (2.0 kW)", r1)
    new_r2 = st.toggle("Relay 2 (1.5 kW)", r2)
    new_r3 = st.toggle("Relay 3 (1.0 kW)", r3)

    if new_r1 != r1 or new_r2 != r2 or new_r3 != r3:
        ref.child("relay_control").set({
            "relay1": int(new_r1),
            "relay2": int(new_r2),
            "relay3": int(new_r3)
        })
        st.rerun()

    if total_power > threshold:
        st.error("🔴 OVERLOAD DETECTED")
    else:
        st.success("🟢 LOAD NORMAL")

# ================= ANALYTICS & REPORTS =================
elif menu == "📊 Analytics":
    st.header("Hourly Energy")
    df = pd.DataFrame({"Hour": list(st.session_state.energy_log.keys()), "Energy": list(st.session_state.energy_log.values())})
    st.bar_chart(df.set_index("Hour"))

elif menu == "📄 Reports":
    st.header("Reports")
    st.write("Daily Energy Log:", st.session_state.daily_energy)
    report = f"Date: {today}\nToday Energy: {today_energy}\nCost: {today_cost}"
    st.download_button("Download Report", report)
