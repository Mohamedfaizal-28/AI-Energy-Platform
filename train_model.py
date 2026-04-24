import pandas as pd
from sklearn.linear_model import LinearRegression
import pickle

data = pd.read_csv("load_data.csv")

X = data[['Voltage', 'Current', 'Temperature', 'Time']]
y = data['Load']

model = LinearRegression()
model.fit(X, y)

with open("energy_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("Model trained successfully!")