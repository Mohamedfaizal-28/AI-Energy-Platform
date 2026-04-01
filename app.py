import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import joblib

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

# 🔁 AUTO REFRESH
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

# ---------------- LOAD AI MODEL ----------------
model = joblib.load("energy_model.pkl")

# ---------------- SESSION ----------------
if "date" not in st.session_state:
    st.session_state.date = today

if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

if "monthly_energy" not in st.session_state:
    st.session_state.monthly_energy = {}

# ---------------- FIREBASE DATA ----------------
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

# ---------------- AI PREDICTION ----------------
predicted_load = model.predict([[now.hour, voltage, current, temp]])[0]

# TREND
if "prev_load" not in st.session_state:
    st.session_state.prev_load = predicted_load

trend = predicted_load - st.session_state.prev_load
st.session_state.prev_load = predicted_load

# THRESHOLD (TIME BASED)
if 18 <= now.hour <= 22:
    threshold = 4.0
else:
    threshold = 5.0

# AI STATUS
if predicted_load > threshold and trend > 0:
    ai_status = "HIGH RISK"
elif predicted_load > threshold:
    ai_status = "RISK"
else:
    ai_status = "SAFE"

# SEND AI TO FIREBASE
ref.child("AI").set({
    "predicted_load": float(predicted_load),
    "trend": float(trend),
    "status": ai_status
})

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Live Power (W)", round(power, 2))

    # 🔥 AI DISPLAY
    st.metric("Predicted Load (kW)", round(predicted_load, 2))
    st.write(f"Trend: {round(trend,2)}")

    if ai_status == "HIGH RISK":
        st.error("🔴 High Overload Risk")
    elif ai_status == "RISK":
        st.warning("🟠 Moderate Risk")
    else:
        st.success("🟢 System Stable")

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    new_r1 = st.toggle("Relay 1", r1)
    new_r2 = st.toggle("Relay 2", r2)
    new_r3 = st.toggle("Relay 3", r3)

    # 🔥 AI CONTROL
    if predicted_load > threshold:
        st.warning("⚠ AI Optimizing Load")

        if predicted_load > threshold:
            new_r3 = False

        if predicted_load > threshold + 0.5:
            new_r2 = False

        if predicted_load > threshold + 1.0:
            new_r1 = False

    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    st.write({
        "Relay1": new_r1,
        "Relay2": new_r2,
        "Relay3": new_r3
    })

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Hourly Energy")

    hour = now.hour
    power_kw = power / 1000
    energy_inc = power_kw * (3 / 3600)

    st.session_state.energy_log[hour] += energy_inc

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))

# ================= REPORT =================
elif menu == "📄 Reports":

    st.header("Reports")

    today_energy = sum(st.session_state.energy_log.values())
    monthly_energy = st.session_state.monthly_energy.get(month, 0)

    report = f"""
Date: {today}
Today Energy: {today_energy}
Monthly Energy: {monthly_energy}
"""

    st.download_button("Download Report", report)
```
