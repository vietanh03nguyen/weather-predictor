import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
import requests

# -------------------- Setup --------------------

st.set_page_config(page_title="🌦️ Weather Forecast", layout="centered")

st_autorefresh(interval=60 * 1000, key="refresh")

# Load the trained model
models = joblib.load("./weather_models.pkl")
features = list(models.keys())

# MongoDB setup
MONGO_URI = "mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
collection = client["weather_db"]["realtime_weather"]

lat, lon = 21.00, 105.88  # Hanoi coordinates
open_meteo_url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}&current=apparent_temperature&timezone=Asia%2FBangkok"
)

try:
    response = requests.get(open_meteo_url)
    response.raise_for_status()
    current_apparent_temp = response.json()["current"]["apparent_temperature"]
except Exception as e:
    st.error("⚠️ Could not fetch current apparent temperature.")
    current_apparent_temp = None

# Get latest records (last 2 to enable lag)
latest_data = list(collection.find().sort("timestamp", -1).limit(2))
if len(latest_data) < 2:
    st.warning("⚠️ Not enough data in MongoDB to perform prediction.")
    st.stop()

# Format latest records to DataFrame
df = pd.DataFrame(latest_data)
df = df.sort_values("timestamp")  # Ascending
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)

# Rename to match model training
df = df.rename(columns={
    'relative_humidity_2m_percent': 'humidity',
    'surface_pressure_hPa': 'pressure',
    'wind_speed_10m_kmh': 'wind_speed',
    'cloud_cover_percent': 'cloud_cover',
    'precipitation_probability_percent': 'precip_prob',
    'temperature_2m_C': 'temp'
})

# Ensure correct column order
df = df[features]

# -------------------- UI --------------------

st.title("🌤️ Real-Time Weather Forecast")

# Local time
local_tz = ZoneInfo("Asia/Ho_Chi_Minh")
local_time = datetime.now(local_tz).replace(second=0, microsecond=0)
st.subheader(f"📅Hanoi Local Time: {local_time.strftime('%Y-%m-%d %H:%M')}")

# -------------------- Current Weather --------------------
st.markdown("---")
st.markdown("### 🌡️ Current Weather")
if current_apparent_temp is not None:
    st.metric("Feels Like (°C)", f"{current_apparent_temp:.2f}")
col1, col2 = st.columns(2)
with col1:
    st.metric("Temperature (°C)", f"{df.iloc[-1]['temp']:.2f}")
    st.metric("Humidity (%)", f"{df.iloc[-1]['humidity']:.2f}")
    st.metric("Cloud Cover (%)", f"{df.iloc[-1]['cloud_cover']:.2f}")

with col2:
    st.metric("Wind Speed (km/h)", f"{df.iloc[-1]['wind_speed']:.2f}")
    st.metric("Precipitation Probability (%)", f"{df.iloc[-1]['precip_prob']:.2f}")
    st.metric("Surface Pressure (hPa)", f"{df.iloc[-1]['pressure']:.2f}")


# Slider for prediction horizon
hours_ahead = st.slider("⏱️ Forecast range (hours)", min_value=1, max_value=96, value=6)

# -------------------- Prediction --------------------

# Use the most recent record for lag-based prediction
current = df.iloc[-1].copy()
utc_base_time = df.index[-1].tz_localize("UTC")  # localize to UTC first

forecast_times = [
    (utc_base_time + timedelta(hours=i+1)).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    for i in range(hours_ahead)
]
forecast_df = pd.DataFrame(index=forecast_times, columns=features)

for hour in range(hours_ahead):
    input_data = current[features].values.reshape(1, -1)

    for feature in features:
        model = models[feature]
        prediction = model.predict(input_data)[0]
        forecast_df.loc[forecast_times[hour], feature] = prediction

    # Use predictions for next round's lag
    current = forecast_df.loc[forecast_times[hour]]

# Display forecast table
st.markdown("### 📈 Forecast Charts")
tabs = st.tabs([f"{feature.title()}" for feature in features])

for i, feature in enumerate(features):
    with tabs[i]:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(forecast_df.index, forecast_df[feature], label='Predicted', marker='o', color='tab:blue')
        ax.set_title(f"{feature.title()} Forecast")
        ax.set_xlabel("Time")
        ax.set_ylabel(feature)
        ax.grid(True)
        st.pyplot(fig)
st.markdown("### 🔮 Predicted Weather")
st.dataframe(forecast_df.round(2))




