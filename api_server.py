from fastapi import FastAPI
import joblib
import numpy as np

app = FastAPI()

# Load AI model
model = joblib.load("energy_model.pkl")

# Store latest data (temporary memory)
latest_data = {
    "voltage": 0,
    "current": 0,
    "temperature": 0,
    "hour": 0,
    "predicted_load": 0
}

# Store relay states (manual + auto)
relay_state = {
    "relay1": True,
    "relay2": True,
    "relay3": True
}

# ---------------- HOME ----------------
@app.get("/")
def home():
    return {"message": "AI API Running"}

# ---------------- ESP32 SEND DATA ----------------
@app.post("/update")
def update_data(hour: int, voltage: float, current: float, temp: float):

    data = np.array([[hour, voltage, current, temp]])
    prediction = model.predict(data)[0]
    prediction = round(prediction, 2)

    # Save latest data
    latest_data["hour"] = hour
    latest_data["voltage"] = voltage
    latest_data["current"] = current
    latest_data["temperature"] = temp
    latest_data["predicted_load"] = prediction

    # AUTO RELAY LOGIC
    threshold = 4.5

    if prediction > threshold:
        relay_state["relay3"] = False
        relay_state["relay2"] = False
        relay_state["relay1"] = False
    else:
        relay_state["relay1"] = True
        relay_state["relay2"] = True
        relay_state["relay3"] = True

    return {
        "predicted_load": prediction,
        "relay1": relay_state["relay1"],
        "relay2": relay_state["relay2"],
        "relay3": relay_state["relay3"]
    }

# ---------------- ESP32 GET RELAY ----------------
@app.get("/relay")
def get_relay():
    return relay_state

# ---------------- DASHBOARD GET DATA ----------------
@app.get("/data")
def get_data():
    return latest_data

# ---------------- MANUAL CONTROL ----------------
@app.post("/set_relay")
def set_relay(r1: bool, r2: bool, r3: bool):

    relay_state["relay1"] = r1
    relay_state["relay2"] = r2
    relay_state["relay3"] = r3

    return {"message": "Relay updated"}
