from pymongo import MongoClient
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import os
import time

st.set_page_config(page_title="Current Weather", layout="centered")

# Auto-refresh every 60 seconds
st_autorefresh(interval= 3600 * 1000, key="refresh")

# MongoDB Setup
MONGO_URI = "mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["weather_db"]
collection = db["realtime_weather"]

# Load latest record
latest_record = collection.find_one(sort=[("timestamp", -1)])

# Streamlit app title
st.title("🌤️ Current Weather Data")

# Timezone
local_tz = ZoneInfo("Asia/Ho_Chi_Minh")  # Change to your local timezone

# Create an empty placeholder to update time
time_placeholder = st.empty()

if latest_record:
    col1, col2 = st.columns(2)

    with col1:
        st.metric("🌡️ Temperature (°C)", f"{latest_record['temperature_2m_C']} °C")
        st.metric("💧 Humidity (%)", f"{latest_record['relative_humidity_2m_percent']} %")
        st.metric("☁️ Cloud Cover (%)", f"{latest_record['cloud_cover_percent']} %")

    with col2:
        st.metric("🌬️ Wind Speed (km/h)", f"{latest_record['wind_speed_10m_kmh']} km/h")
        st.metric("🌧️ Precipitation Probability", f"{latest_record['precipitation_probability_percent']} %")
        st.metric("🧭 Surface Pressure (hPa)", f"{latest_record['surface_pressure_hPa']}")

    st.markdown("---")
    st.caption("⏱️ Time updates every second | Weather data refreshes every 60 seconds")
else:
    st.warning("⚠️ No weather data available yet.")

# Update time every second (in-place only)
for i in range(60):
    local_time = datetime.now(local_tz)
    time_placeholder.subheader(f"📅 Local Time: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(1)

# Display weather only once per refresh

