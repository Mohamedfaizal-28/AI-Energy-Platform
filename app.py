import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

# AUTO REFRESH
st_autorefresh(interval=3000, key="refresh")

st.set_page_config(page_title="AI Energy System", layout="wide")

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_secret)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')

# ---------------- SESSION ----------------
if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# ---------------- READ FIREBASE ----------------
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

# ---------------- TIME ----------------
now = datetime.now()
current_hour = now.hour

# ---------------- ENERGY ----------------
interval_sec = 3
energy_increment = power * (interval_sec / 3600)

st.session_state.energy_log[current_hour] += energy_increment

total_energy = sum(st.session_state.energy_log.values())
cost = total_energy * 8

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ Smart Energy Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Power (kW)", power)

    col4, col5 = st.columns(2)
    col4.metric("Total Energy (kWh)", round(total_energy,3))
    col5.metric("Cost (₹)", round(cost,2))

    if power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control (Firebase Connected)")

    new_r1 = st.toggle("Relay 1", value=relay1)
    new_r2 = st.toggle("Relay 2", value=relay2)
    new_r3 = st.toggle("Relay 3", value=relay3)

    # WRITE TO FIREBASE
    ref.child("relay_control").set({
        "relay1": int(new_r1),
        "relay2": int(new_r2),
        "relay3": int(new_r3)
    })

    st.success("Relay state synced to Firebase")

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Hourly Energy Consumption")

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))

    st.info(f"Current Time: {now.strftime('%H:%M:%S')}")

# ================= REPORT =================
elif menu == "📄 Reports":

    st.header("Energy Report")

    st.write(f"Voltage: {voltage} V")
    st.write(f"Current: {current} A")
    st.write(f"Temperature: {temp} °C")
    st.write(f"Power: {power} kW")

    st.subheader("Relay State")
    st.write({
        "Relay1": relay1,
        "Relay2": relay2,
        "Relay3": relay3
    })

    st.subheader("Hourly Energy")
    st.write(st.session_state.energy_log)

    st.subheader("Total")
    st.write(f"Energy: {round(total_energy,3)} kWh")
    st.write(f"Cost: ₹ {round(cost,2)}")

    report = f"""
ENERGY REPORT
-------------
Voltage: {voltage}
Current: {current}
Temperature: {temp}
Power: {power}

Relay State:
{relay_fb}

Hourly Energy:
{st.session_state.energy_log}

Total Energy: {round(total_energy,3)} kWh
Cost: ₹{round(cost,2)}
"""

    st.download_button("Download Report", report)
