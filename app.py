import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz

# AUTO REFRESH
st_autorefresh(interval=2000, key="refresh")

# PAGE
st.set_page_config(page_title="AI Energy SCADA", layout="wide")

# 🎨 SCADA UI (IMPROVED)
st.markdown("""
<style>
body {
    background-color: #0b0f1a;
    color: #e6edf3;
}
.card {
    background: #111827;
    padding: 15px;
    border-radius: 12px;
    margin: 5px;
}
.blink {
    animation: blink 1s infinite;
}
@keyframes blink {
    50% {opacity: 0.3;}
}
</style>
""", unsafe_allow_html=True)

# ---------------- TIME ----------------
india = pytz.timezone('Asia/Kolkata')
now = datetime.now(india)

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙ Control Panel")

menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🔌 Relay Control"
])

# ---------------- DEMO SLIDER ----------------
if "slider" not in st.session_state:
    st.session_state.slider = 0.0

sim = st.sidebar.slider("⚡ Simulated Load", 0.0, 7.5, st.session_state.slider)

# ---------------- RELAY STATE ----------------
if "relay" not in st.session_state:
    st.session_state.relay = {
        "r1": True,
        "r2": True,
        "r3": True
    }

# ---------------- LOAD VALUES ----------------
relay_load = {
    "r1": 2.0,
    "r2": 1.5,
    "r3": 1.0
}

total_power = sim

# ================= AI LOAD SHEDDING =================
cut_load = 0

if total_power > 4.5:

    if 4.51 <= total_power <= 5.5:
        st.session_state.relay["r3"] = False
        cut_load = relay_load["r3"]

    elif 5.51 <= total_power <= 6:
        st.session_state.relay["r2"] = False
        cut_load = relay_load["r2"]

    elif 6.01 <= total_power <= 6.5:
        st.session_state.relay["r1"] = False
        cut_load = relay_load["r1"]

    elif 6.51 <= total_power <= 7.5:
        st.session_state.relay["r1"] = False
        st.session_state.relay["r3"] = False
        cut_load = relay_load["r1"] + relay_load["r3"]

# 🔥 AUTO UPDATE SLIDER AFTER CUT
final_power = max(0, total_power - cut_load)
st.session_state.slider = final_power

# ================= DASHBOARD =================
if menu == "🏠 Dashboard":

    st.title("⚡ AI Energy SCADA Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"<div class='card'>Voltage<br><b>230 V</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'>Current<br><b>2 A</b></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'>Temperature<br><b>32°C</b></div>", unsafe_allow_html=True)

    st.markdown(f"<div class='card'>Live Power<br><b>{round(final_power,2)} kW</b></div>", unsafe_allow_html=True)

    # STATUS
    if final_power > 4.5:
        st.markdown("<div class='card blink' style='color:red'>🔴 OVERLOAD</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='card' style='color:lime'>🟢 NORMAL</div>", unsafe_allow_html=True)

    st.info(f"🕒 Time: {now.strftime('%H:%M:%S')}")

# ================= RELAY CONTROL =================
elif menu == "🔌 Relay Control":

    st.header("Relay Control")

    r1 = st.checkbox("Relay 1 (2kW)", st.session_state.relay["r1"])
    r2 = st.checkbox("Relay 2 (1.5kW)", st.session_state.relay["r2"])
    r3 = st.checkbox("Relay 3 (1kW)", st.session_state.relay["r3"])

    st.session_state.relay["r1"] = r1
    st.session_state.relay["r2"] = r2
    st.session_state.relay["r3"] = r3

    st.write("### Current Relay Status")

    for r, state in st.session_state.relay.items():
        if state:
            st.success(f"{r} ON")
        else:
            st.error(f"{r} OFF")
