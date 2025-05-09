from pymongo import MongoClient
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Current Weather", layout="centered")

# Auto-refresh every 1 hour (3600 seconds)
st_autorefresh(interval=60 * 1000, key="refresh")

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
local_tz = ZoneInfo("Asia/Ho_Chi_Minh")
local_time = datetime.now(local_tz).replace(second=0, microsecond=0)

# Display timestamp at current hour
st.subheader(f"📅 Local Time: {local_time.strftime('%Y-%m-%d %H:%M')}")

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
    st.caption("🔄 Weather data auto-refreshes every hour.")
else:
    st.warning("⚠️ No weather data available yet.")
