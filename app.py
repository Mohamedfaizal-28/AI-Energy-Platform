import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import requests
import time

# ================= FIREBASE =================
FIREBASE_URL = "https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com"

def get_sensor_data():
    try:
        response = requests.get(f"{FIREBASE_URL}/sensors.json")
        return response.json() or {}
    except:
        return {}

def set_relay(relay_num, state):
    try:
        requests.put(
            f"{FIREBASE_URL}/relays/relay{relay_num}.json",
            json=(1 if state else 0)
        )
        return True
    except:
        return False

def get_relay_states():
    try:
        response = requests.get(f"{FIREBASE_URL}/relays.json")
        return response.json() or {}
    except:
        return {}

# ================= LOGIN =================

def check_login(username, password):
    return username == "admin" and password == "1234"

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.title("🔐 AI Energy Platform Login")
    user = st.text_input("Username")
    pwd  = st.text_input("Password", type="password")
    if st.button("Login"):
        if check_login(user, pwd):
            st.session_state.role = "admin"
            st.success("Admin Login Successful")
            st.rerun()
        else:
            st.session_state.role = "user"
            st.success("User Mode Access Granted")
            st.rerun()
    st.stop()

# ================= DATABASE =================

conn   = sqlite3.connect("energy_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS energy_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    hour INTEGER,
    voltage REAL,
    current REAL,
    temperature REAL,
    predicted_load REAL,
    status TEXT
)
""")
conn.commit()

# ================= SIDEBAR =================

threshold = 4.5

st.sidebar.title("⚙ System Control Panel")
st.sidebar.write(f"Logged in as: {st.session_state.role}")
st.sidebar.write(f"Threshold: {threshold} kW")

if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

auto_refresh = st.sidebar.checkbox("🔄 Auto Refresh (5s)", value=True)

# ================= LOAD MODEL =================

try:
    model = joblib.load("energy_model.pkl")
except:
    st.error("AI model not found")
    st.stop()

# ================= LIVE DATA =================

st.title("⚡ AI Smart Energy Management System")
st.subheader("📡 Live ESP32 Sensor Data")

sensor_data = get_sensor_data()

if sensor_data:
    st.metric("Voltage", f"{sensor_data.get('voltage','--')} V")
    st.metric("Current", f"{sensor_data.get('current','--')} A")
    st.metric("Power", f"{sensor_data.get('power','--')} W")
    st.metric("Temperature", f"{sensor_data.get('temperature','--')} °C")
else:
    st.warning("Waiting for ESP32 data...")

# ================= INPUT =================

hour = st.slider("Hour", 0, 23, datetime.now().hour)
voltage = st.number_input("Voltage", value=230.0)
current = st.number_input("Current", value=2.0)
temp = st.number_input("Temperature", value=30.0)

prediction = round(model.predict([[hour, voltage, current, temp]])[0], 2)
st.metric("Predicted Load", prediction)

# ================= OVERLOAD =================

if prediction > threshold:
    st.error("OVERLOAD!")
else:
    st.success("NORMAL")

# ================= RELAY =================

st.subheader("Relay Control")

relay_states = get_relay_states()

r1 = relay_states.get('relay1', 0)
r2 = relay_states.get('relay2', 0)
r3 = relay_states.get('relay3', 0)

if st.button("Toggle Relay 1"):
    set_relay(1, not r1)

if st.button("Toggle Relay 2"):
    set_relay(2, not r2)

if st.button("Toggle Relay 3"):
    set_relay(3, not r3)

# ================= AUTO REFRESH =================

if auto_refresh:
    time.sleep(5)
    st.rerun()
