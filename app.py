import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# 🔥 NEW: Firebase
import firebase_admin
from firebase_admin import credentials, db

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:

    firebase_secret = st.secrets["firebase"]

    cred = credentials.Certificate(firebase_secret)

    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://ai-energy-system-c6b9c-default-rtdb.firebaseio.com/'
    })

ref = db.reference('/')
# ---------------- LOGIN ----------------
def check_login(username, password):
    return username == "Admin" and password == "1234"

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:

    st.title("🔐 AI Energy Platform Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):

        if check_login(user, pwd):
            st.session_state.role = "Admin"
            st.success("Admin Login Successful")
            st.rerun()

        elif user == "User" and pwd == "1234":
            st.session_state.role = "User"
            st.success("User Login Successful")
            st.rerun()

        else:
            st.error("Invalid credentials")

    st.stop()

# ---------------- DASHBOARD ----------------
st.title("⚡ AI Smart Energy Management System")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("energy_data.db", check_same_thread=False)
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

# ---------------- LOAD MODEL ----------------
model = joblib.load("energy_model.pkl")

# ---------------- GET DATA FROM FIREBASE ----------------
data = ref.child("sensor_data").get()

if data:
    voltage = data.get("voltage", 0)
    current = data.get("current", 0)
    temp = data.get("temperature", 0)
else:
    voltage, current, temp = 0, 0, 0

hour = datetime.now().hour

# ---------------- SHOW SENSOR DATA ----------------
st.subheader("📡 Live Sensor Data")
st.write(f"Voltage: {voltage} V")
st.write(f"Current: {current} A")
st.write(f"Temperature: {temp} °C")

# ---------------- PREDICTION ----------------
input_data = np.array([[hour, voltage, current, temp]])
prediction = round(model.predict(input_data)[0], 2)

st.metric("Predicted Load (kW)", prediction)

threshold = 4.5

# ---------------- OVERLOAD LOGIC ----------------
if prediction > threshold:
    st.error("⚠ OVERLOAD DETECTED")
else:
    st.success("✅ NORMAL LOAD")

# ---------------- AUTO RELAY CONTROL ----------------
relay_loads = {
    "relay1": 0.2,
    "relay2": 0.5,
    "relay3": 1.0
}

relay_status = {
    "relay1": 1,
    "relay2": 1,
    "relay3": 1
}

if prediction > threshold:
    overload = prediction - threshold

    for r, load in relay_loads.items():
        if overload > 0:
            relay_status[r] = 0
            overload -= load

# ---------------- MANUAL CONTROL ----------------
st.subheader("🕹 Manual Control")

relay1 = st.toggle("Relay 1", value=bool(relay_status["relay1"]))
relay2 = st.toggle("Relay 2", value=bool(relay_status["relay2"]))
relay3 = st.toggle("Relay 3", value=bool(relay_status["relay3"]))

# ---------------- SEND TO FIREBASE ----------------
ref.child("relay_control").set({
    "relay1": int(relay1),
    "relay2": int(relay2),
    "relay3": int(relay3)
})

st.success("✅ Relay Status Sent to Firebase")

# ---------------- SAVE DATA ----------------
cursor.execute("""
INSERT INTO energy_log
(timestamp, hour, voltage, current, temperature, predicted_load, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    hour,
    voltage,
    current,
    temp,
    prediction,
    "OVERLOAD" if prediction > threshold else "NORMAL"
))

conn.commit()

# ---------------- DISPLAY HISTORY ----------------
st.subheader("📊 History")
df = pd.read_sql_query("SELECT * FROM energy_log ORDER BY id DESC LIMIT 5", conn)
st.dataframe(df)
