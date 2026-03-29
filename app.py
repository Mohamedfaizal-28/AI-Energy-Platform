import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

# 🔥 AUTO REFRESH
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="refresh")

# 🔥 PAGE CONFIG
st.set_page_config(
    page_title="AI Energy System",
    page_icon="⚡",
    layout="wide"
)

# 🎨 GLASS UI
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
}
.stMetric {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.1);
}
h1, h2, h3 {
    color: #00ffd5;
}
</style>
""", unsafe_allow_html=True)

# 🔥 FIREBASE
import firebase_admin
from firebase_admin import credentials, db

if not firebase_admin._apps:
    firebase_secret = dict(st.secrets["firebase"])
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

# ---------------- SIDEBAR ----------------
threshold = 4.5

st.sidebar.title("⚙ Control Panel")
menu = st.sidebar.radio("Navigation", [
    "🏠 Dashboard",
    "🤖 AI Prediction",
    "🔌 Relay Control",
    "📊 Analytics",
    "📄 Reports"
])

st.sidebar.write(f"Logged in as: {st.session_state.role}")
st.sidebar.write(f"Threshold: {threshold} kW")

if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

# ---------------- LOAD MODEL ----------------
try:
    model = joblib.load("energy_model.pkl")
except:
    st.error("Upload energy_model.pkl")
    st.stop()

# ---------------- DATA ----------------
hour = st.slider("Select Hour (0-23)", 0, 23, 12)

data = ref.child("sensor_data").get()

if data:
    voltage = data.get("voltage") or 230
    current = data.get("current") or 2
    temp = data.get("temperature") or 30
else:
    voltage, current, temp = 230, 2, 30

input_data = np.array([[hour, voltage, current, temp]])
prediction = round(model.predict(input_data)[0], 2)

# ---------------- ADMIN RETRAIN ----------------
if st.session_state.role == "Admin":
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
            st.sidebar.success("Model Retrained!")
        else:
            st.sidebar.warning("Not enough data")

# ========================= PAGES =========================

# 🏠 DASHBOARD
if menu == "🏠 Dashboard":

    st.title("⚡ Smart Energy Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Voltage", f"{voltage} V")
    col2.metric("Current", f"{current} A")
    col3.metric("Temperature", f"{temp} °C")

    st.metric("Predicted Load (kW)", prediction)

    if prediction > threshold:
        st.error("🔴 OVERLOAD DETECTED")
        st.toast("⚠ Reduce Load Immediately!")
    else:
        st.success("🟢 SYSTEM STABLE")

    st.metric("Energy Saving Potential", round(max(0, prediction - threshold), 2))

    st.subheader("🤖 AI Suggestion")
    if prediction > threshold:
        st.warning("Turn OFF non-essential loads")
    else:
        st.success("System running efficiently")

# 🤖 AI PREDICTION
elif menu == "🤖 AI Prediction":

    st.header("AI Load Prediction")

    st.metric("Predicted Load (kW)", prediction)

    status = "OVERLOAD" if prediction > threshold else "NORMAL"

    cursor.execute("""
    INSERT INTO energy_log
    (timestamp, hour, voltage, current, temperature, predicted_load, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hour, voltage, current, temp, prediction, status
    ))
    conn.commit()

# 🔌 RELAY CONTROL
elif menu == "🔌 Relay Control":

    st.header("Smart Relay Control")

    relay1 = st.toggle("Relay 1", True)
    relay2 = st.toggle("Relay 2", True)
    relay3 = st.toggle("Relay 3", True)

    ref.child("relay_control").set({
        "relay1": int(relay1),
        "relay2": int(relay2),
        "relay3": int(relay3)
    })

# 📊 ANALYTICS
elif menu == "📊 Analytics":

    st.header("Energy Analytics")

    data = pd.read_csv("load_data.csv")

    fig, ax = plt.subplots()
    ax.plot(data["hour"], data["load"], linewidth=3)
    ax.axhline(y=threshold, linestyle='--', linewidth=2)
    ax.scatter(hour, prediction, s=150)

    ax.set_facecolor("#111")
    fig.patch.set_facecolor("#111")

    st.pyplot(fig)

# 📄 REPORTS
elif menu == "📄 Reports":

    st.header("Download Report")

    electricity_rate = 8
    monthly_bill = prediction * 24 * 30 * electricity_rate

    report = f"""
AI Smart Energy Report
----------------------
Hour: {hour}
Voltage: {voltage} V
Current: {current} A
Temperature: {temp} °C
Predicted Load: {prediction} kW
Estimated Monthly Bill: ₹ {round(monthly_bill,2)}
"""

    st.download_button("Download Report", report)

    if st.session_state.role == "Admin":
        st.subheader("History")

        data_log = pd.read_sql_query(
            "SELECT * FROM energy_log ORDER BY id DESC LIMIT 10",
            conn
        )
        st.dataframe(data_log)
