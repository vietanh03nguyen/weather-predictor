import requests
from pymongo import MongoClient
from datetime import datetime
from dateutil import parser

# === 1. MongoDB Setup ===
client = MongoClient("mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority")
db = client["weather_db"]
collection = db["realtime_weather"]

# === 2. Open-Meteo API Setup ===
latitude = 21.0285     # Replace with your location
longitude = 105.8542
timezone = "auto"

weather_params = [
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "pressure_msl", "wind_speed_10m", "cloud_cover", "precipitation_probability"
]

url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={latitude}&longitude={longitude}"
    f"&hourly={','.join(weather_params)}"
    f"&timezone={timezone}"
)

# === 3. Fetch Latest Forecast and Store Only Newest Hour ===
def fetch_latest_and_store():
    response = requests.get(url)
    data = response.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        print("⚠️ No forecast data available.")
        return

    # Get the latest timestamp (last item)
    latest_time_str = times[-1]
    latest_time = parser.isoparse(latest_time_str)

    # Check if data with this timestamp already exists
    if collection.find_one({"timestamp": latest_time}):
        print(f"⏳ Data for {latest_time} already exists. Skipping insert.")
        return

    # Insert latest record
    idx = len(times) - 1
    record = {
        "timestamp": latest_time,
        "temperature_2m_C": hourly["temperature_2m"][idx],
        "relative_humidity_2m_percent": hourly["relative_humidity_2m"][idx],
        "surface_pressure_hPa": hourly["surface_pressure"][idx],
        "pressure_msl_hPa": hourly["pressure_msl"][idx],
        "wind_speed_10m_kmh": hourly["wind_speed_10m"][idx],
        "cloud_cover_percent": hourly["cloud_cover"][idx],
        "precipitation_probability_percent": hourly["precipitation_probability"][idx]
    }

    collection.insert_one(record)
    print(f"✅ Inserted data for {latest_time}")

# === 4. Run Script ===
if __name__ == "__main__":
    fetch_latest_and_store()
