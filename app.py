import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

st.set_page_config(page_title="AI Energy System", layout="wide")

# ---------------- SESSION STORAGE ----------------
if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

if "relay_time" not in st.session_state:
    st.session_state.relay_time = {
        "relay1": 0,
        "relay2": 0,
        "relay3": 0
    }

if "relay_state" not in st.session_state:
    st.session_state.relay_state = {
        "relay1": True,
        "relay2": True,
        "relay3": True
    }

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

# ---------------- SENSOR DATA ----------------
voltage = 230
current = 0.5
temp = 32

# ---------------- RELAY LOAD ----------------
relay_loads = {
    "relay1": 2.0,
    "relay2": 1.5,
    "relay3": 1.0
}

# ---------------- LOAD ----------------
active_load = sum(load for r, load in relay_loads.items() if st.session_state.relay_state[r])

# ---------------- TIME ----------------
now = datetime.now()
current_hour = now.hour

# ---------------- ENERGY UPDATE ----------------
interval_sec = 5

energy_increment = active_load * (interval_sec / 3600)

st.session_state.energy_log[current_hour] += energy_increment

# ---------------- RELAY TIME TRACK ----------------
for r in st.session_state.relay_state:
    if st.session_state.relay_state[r]:
        st.session_state.relay_time[r] += interval_sec

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ Smart Energy Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Active Load (kW)", round(active_load,2))

    total_energy = sum(st.session_state.energy_log.values())
    cost = total_energy * 8

    col4, col5 = st.columns(2)
    col4.metric("Total Energy (kWh)", round(total_energy,3))
    col5.metric("Electricity Cost (₹)", round(cost,2))

    if active_load > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Smart Relay Control")

    st.session_state.relay_state["relay1"] = st.toggle("Relay 1 (2kW)", st.session_state.relay_state["relay1"])
    st.session_state.relay_state["relay2"] = st.toggle("Relay 2 (1.5kW)", st.session_state.relay_state["relay2"])
    st.session_state.relay_state["relay3"] = st.toggle("Relay 3 (1kW)", st.session_state.relay_state["relay3"])

    active_load = sum(load for r, load in relay_loads.items() if st.session_state.relay_state[r])
    st.metric("Current Load (kW)", active_load)

    # AI optimization
    if active_load > threshold:

        st.error("⚠ Overload Predicted")

        overload = active_load - threshold

        if overload <= 1:
            st.session_state.relay_state["relay3"] = False
        elif overload <= 2:
            st.session_state.relay_state["relay2"] = False
        else:
            st.session_state.relay_state["relay1"] = False

        st.warning("AI optimized load")

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Hourly Energy Consumption")

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy (kWh)": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))

    st.info(f"Current Time: {now.strftime('%H:%M:%S')}")

# ================= REPORT =================
elif menu == "📄 Reports":

    st.header("Energy Report")

    total_energy = sum(st.session_state.energy_log.values())
    cost = total_energy * 8

    st.subheader("System Summary")

    st.write(f"Voltage: {voltage} V")
    st.write(f"Current: {current} A")
    st.write(f"Temperature: {temp} °C")

    st.subheader("Relay Status")

    for r, state in st.session_state.relay_state.items():
        st.write(f"{r}: {'ON' if state else 'OFF'}")

    st.subheader("Relay Usage Time (seconds)")

    for r, t in st.session_state.relay_time.items():
        st.write(f"{r}: {t} sec")

    st.subheader("Hourly Energy")

    st.write(st.session_state.energy_log)

    st.subheader("Total")

    st.write(f"Energy Used: {round(total_energy,3)} kWh")
    st.write(f"Cost: ₹ {round(cost,2)}")

    # DOWNLOAD REPORT
    report = f"""
ENERGY REPORT
-------------
Voltage: {voltage}
Current: {current}
Temperature: {temp}

Relay States:
{st.session_state.relay_state}

Relay Usage Time (sec):
{st.session_state.relay_time}

Hourly Energy:
{st.session_state.energy_log}

Total Energy: {round(total_energy,3)} kWh
Cost: ₹{round(cost,2)}
"""

    st.download_button("Download Report", report)
