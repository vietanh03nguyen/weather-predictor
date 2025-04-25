import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression
import joblib
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- Settings ---
MODEL_PATH = "weather_models.pkl"
OLD_DATA_PATH = 'open-meteo-21.00N105.88E10m.csv'
USE_OLD_DATA = os.path.exists(OLD_DATA_PATH)

# --- Load old data ---
if USE_OLD_DATA:
    old_df = pd.read_csv('open-meteo-21.00N105.88E10m.csv', skiprows=2, parse_dates=['time'])
    old_df.set_index("time", inplace=True)
else:
    old_df = pd.DataFrame()

# --- Load new data from MongoDB ---
MONGO_URI = "mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
collection = client["weather_db"]["realtime_weather"]
docs = list(collection.find())

if len(docs) < 2:
    print("❌ Not enough new data.")
    exit()

new_df = pd.DataFrame(docs)
new_df["timestamp"] = pd.to_datetime(new_df["timestamp"])
new_df.set_index("timestamp", inplace=True)
new_df = new_df.sort_index()

# --- Rename columns ---
new_df = new_df.rename(columns={
    'relative_humidity_2m_percent': 'humidity',
    'surface_pressure_hPa': 'pressure',
    'wind_speed_10m_kmh': 'wind_speed',
    'cloud_cover_percent': 'cloud_cover',
    'precipitation_probability_percent': 'precip_prob',
    'temperature_2m_C': 'temp'
})

features = ['humidity', 'pressure', 'wind_speed', 'cloud_cover', 'precip_prob', 'temp']
new_df = new_df[features]

# --- Combine old + new ---
combined_df = pd.concat([old_df, new_df])
combined_df = combined_df[~combined_df.index.duplicated()]
combined_df = combined_df.resample("1H").mean().interpolate(method="time")

# --- Save merged data ---
combined_df.to_csv("historical_weather.csv")

# --- Lagged features ---
X_lag = combined_df.shift(1).dropna()
Y = combined_df.loc[X_lag.index]

# --- Train Linear Regression models ---
models = {}
for col in features:
    model = LinearRegression()
    model.fit(X_lag, Y[col])
    models[col] = model

# --- Save models ---
# joblib.dump(models, MODEL_PATH)
print("✅ Retrained models saved to 'weather_models.pkl'")

# --- Optionally clear MongoDB ---
# collection.delete_many({})
print(f"🗑️ Cleared {len(new_df)} new records from MongoDB.")

# --- Visualization ---
sns.set(style="whitegrid")
fig, axs = plt.subplots(3, 2, figsize=(15, 10))
fig.suptitle("Weather Data Trends", fontsize=16)

plot_colors = ['tab:red', 'tab:blue', 'tab:green', 'tab:purple', 'tab:orange', 'tab:brown']

for i, col in enumerate(features):
    ax = axs[i // 2][i % 2]
    ax.plot(combined_df.index, combined_df[col], label=col, color=plot_colors[i])
    ax.set_title(f"{col.capitalize()} Over Time")
    ax.set_xlabel("Time")
    ax.set_ylabel(col.capitalize())
    ax.grid(True)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()
