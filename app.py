import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# PAGE
st.set_page_config(page_title="AI Energy System", layout="wide")

# ---------------- SESSION STORAGE ----------------
if "energy_log" not in st.session_state:
    st.session_state.energy_log = {i: 0 for i in range(24)}

if "total_energy" not in st.session_state:
    st.session_state.total_energy = 0

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control",
    "📊 Analytics"
])

# ---------------- SIMULATED SENSOR ----------------
# (Replace later with Firebase)
voltage = 230
current = 0.5   # base current
temp = 32

# ---------------- RELAY LOAD ----------------
relay_loads = {
    "relay1": 2.0,
    "relay2": 1.5,
    "relay3": 1.0
}

# ---------------- RELAY STATE ----------------
if "relay_state" not in st.session_state:
    st.session_state.relay_state = {
        "relay1": True,
        "relay2": True,
        "relay3": True
    }

# ---------------- LOAD CALCULATION ----------------
active_load = sum(load for r, load in relay_loads.items() if st.session_state.relay_state[r])

real_power = round(active_load, 2)

# ---------------- ENERGY UPDATE ----------------
hour = datetime.now().hour

energy_increment = real_power * (5/3600)  # 5 sec interval
st.session_state.energy_log[hour] += energy_increment
st.session_state.total_energy += energy_increment

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ Smart Energy Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Active Load (kW)", real_power)

    # COST
    cost = st.session_state.total_energy * 8

    col4, col5 = st.columns(2)
    col4.metric("Total Energy (kWh)", round(st.session_state.total_energy,3))
    col5.metric("Electricity Cost (₹)", round(cost,2))

    if real_power > threshold:
        st.error("🔴 OVERLOAD")
    else:
        st.success("🟢 NORMAL")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Smart Relay Control")

    # Manual switches
    st.session_state.relay_state["relay1"] = st.toggle("Relay 1 (2 kW)", st.session_state.relay_state["relay1"])
    st.session_state.relay_state["relay2"] = st.toggle("Relay 2 (1.5 kW)", st.session_state.relay_state["relay2"])
    st.session_state.relay_state["relay3"] = st.toggle("Relay 3 (1 kW)", st.session_state.relay_state["relay3"])

    # Show load
    active_load = sum(load for r, load in relay_loads.items() if st.session_state.relay_state[r])
    st.metric("Current Load (kW)", active_load)

    # ---------------- AI LOGIC ----------------
    if active_load > threshold:

        st.error("⚠ Overload Predicted")

        overload = active_load - threshold

        # Smart optimization
        if overload <= 1:
            st.session_state.relay_state["relay3"] = False
        elif overload <= 2:
            st.session_state.relay_state["relay2"] = False
        else:
            st.session_state.relay_state["relay1"] = False

        st.warning("AI optimized the load by turning OFF relays")

# ================= ANALYTICS =================
elif menu == "📊 Analytics":

    st.header("Hourly Energy Consumption")

    df = pd.DataFrame({
        "Hour": list(st.session_state.energy_log.keys()),
        "Energy": list(st.session_state.energy_log.values())
    })

    st.bar_chart(df.set_index("Hour"))
