import pandas as pd
from sklearn.linear_model import LinearRegression
import pickle

# Load dataset
data = pd.read_csv("load_data.csv")

# Input features
X = data[['Voltage', 'Current', 'Temperature', 'Time']]

# Output
y = data['Load']

# Create model
model = LinearRegression()

# Train model
model.fit(X, y)

# Save model
with open("energy_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("Model trained and saved as energy_model.pkl")
