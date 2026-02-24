import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# ------------------ LOGIN SYSTEM ------------------

def check_login(username, password):
    return username == "admin" and password == "1234"

if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:

    st.title("🔐 AI Energy Platform Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

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

# ------------------ DATABASE SETUP ------------------

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

# ------------------ SIDEBAR ------------------

threshold = 4.5
st.sidebar.title("⚙ System Control Panel")
st.sidebar.write(f"Logged in as: {st.session_state.role}")
st.sidebar.write(f"Threshold: {threshold} kW")

# ------------------ RETRAIN (ADMIN ONLY) ------------------

if st.session_state.role == "admin":
    if st.sidebar.button("🔄 Retrain AI Model"):

        df = pd.read_sql_query(
            "SELECT hour, voltage, current, temperature, predicted_load FROM energy_log",
            conn
        )

        if len(df) > 10:
            X = df[['hour','voltage','current','temperature']]
            y = df['predicted_load']

            new_model = LinearRegression()
            new_model.fit(X, y)

            joblib.dump(new_model, "energy_model.pkl")
            st.sidebar.success("AI Model Retrained Successfully!")
        else:
            st.sidebar.warning("Not enough data to retrain.")

# ------------------ PAGE TITLE ------------------

st.title("⚡ AI Smart Energy Management System")
st.subheader("Predictive Load Monitoring Dashboard")

# ------------------ LOAD MODEL ------------------

model = joblib.load("energy_model.pkl")

# ------------------ USER INPUTS ------------------

hour = st.slider("Select Hour (0-23)", 0, 23, 12)
voltage = st.number_input("Voltage (V)", value=230.0)
current = st.number_input("Current (A)", value=2.0)
temp = st.number_input("Temperature (°C)", value=30.0)

# ------------------ PREDICTION ------------------

input_data = [[hour, voltage, current, temp]]
prediction = model.predict(input_data)[0]
prediction = round(prediction, 2)

st.metric("Predicted Load (kW)", prediction)

# ------------------ OVERLOAD LOGIC ------------------

if prediction > threshold:

    required_reduction = round(prediction - threshold, 2)

    st.error("⚠ OVERLOAD DETECTED")
    st.warning(f"Required Load Reduction: {required_reduction} kW")

    adjusted_load = threshold
    st.success(f"Adjusted Load: {adjusted_load} kW")

    energy_saved = required_reduction * 1
    st.info(f"Estimated Energy Saved: {round(energy_saved,2)} kWh")

else:
    st.success("✅ NORMAL LOAD - All Systems Stable")

# ------------------ SMART DATABASE SAVE ------------------

if "last_entry" not in st.session_state:
    st.session_state.last_entry = None

current_entry = (hour, voltage, current, temp, prediction)

if st.session_state.last_entry != current_entry:

    status = "OVERLOAD" if prediction > threshold else "NORMAL"

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
        status
    ))

    conn.commit()
    st.session_state.last_entry = current_entry

# ------------------ RELAY SIMULATION ------------------

st.subheader("🔌 Relay Control Simulation")

if prediction > threshold:
    st.error("Relay 1 (Decorative Load): OFF")
    st.error("Relay 2 (Extra Fans): OFF")
    st.success("Relay 3 (Essential Load): ON")
else:
    st.success("All Relays: ON")

# ------------------ ELECTRICITY BILL ------------------

st.subheader("💰 Estimated Electricity Cost")

electricity_rate = 8
daily_energy = prediction * 24
monthly_energy = daily_energy * 30
monthly_bill = monthly_energy * electricity_rate

st.write(f"Daily Consumption: {round(daily_energy,2)} kWh")
st.write(f"Monthly Consumption: {round(monthly_energy,2)} kWh")
st.success(f"Estimated Monthly Bill: ₹ {round(monthly_bill,2)}")

# ------------------ LOAD CURVE GRAPH ------------------

data = pd.read_csv("load_data.csv")
hours = data["hour"]
actual_load = data["load"]

fig, ax = plt.subplots()

ax.plot(hours, actual_load, marker='o', label="Load")

ax.fill_between(hours, actual_load, threshold,
                where=(actual_load > threshold),
                color='red', alpha=0.3, label="Overload Zone")

ax.axhline(y=threshold, linestyle='--', label="Threshold")

ax.scatter(hour, prediction, color='green', s=120, label="Current Prediction")

ax.set_xlabel("Hour")
ax.set_ylabel("Load (kW)")
ax.set_title("Realistic 24-Hour Load Curve")
ax.legend()

st.pyplot(fig)

# ------------------ SOLAR VS LOAD ------------------

solar_generation = [0,0,0,0,0,0.5,1,2,3,4,5,5.5,6,6,5.5,5,4,3,2,1,0.5,0,0,0]

fig2, ax2 = plt.subplots()
ax2.plot(hours, actual_load, label="Load")
ax2.plot(hours, solar_generation, label="Solar Generation")

ax2.set_xlabel("Hour")
ax2.set_ylabel("Power (kW)")
ax2.set_title("Load vs Solar Generation")
ax2.legend()

st.pyplot(fig2)

# ------------------ DOWNLOAD REPORT ------------------

report_data = f"""
AI Smart Energy Management Report
----------------------------------
Hour: {hour}
Voltage: {voltage} V
Current: {current} A
Temperature: {temp} °C
Predicted Load: {prediction} kW
Threshold: {threshold} kW
Estimated Monthly Bill: ₹ {round(monthly_bill,2)}
"""

st.download_button("📄 Download Report",
                   report_data,
                   file_name="energy_report.txt")

# ------------------ DATABASE VIEW (ADMIN ONLY) ------------------

if st.session_state.role == "admin":
    st.subheader("📊 Logged Prediction History")

    data_log = pd.read_sql_query(
        "SELECT * FROM energy_log ORDER BY id DESC LIMIT 10",
        conn
    )

    st.dataframe(data_log)