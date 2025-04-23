import requests
from pymongo import MongoClient
from datetime import datetime
from dateutil import parser, tz
import time

# === 1. MongoDB Setup ===
client = MongoClient("mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority")
db = client["weather_db"]
collection = db["realtime_weather"]

# === Open-Meteo API Setup ===
latitude = 21.0285
longitude = 105.8542
timezone = "auto"  # Use local timezone in API response

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

# === Fetch Latest Valid Past Record (not future) ===
def fetch_latest_past_hour_and_store():
    response = requests.get(url)
    data = response.json()
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        print("⚠️ No data returned from Open-Meteo.")
        return

    # Get current local time
    local_now = datetime.now(tz=tz.tzlocal())

    # Parse and filter timestamps: only keep ones ≤ now
    parsed_times = [parser.isoparse(t).astimezone(tz.tzlocal()) for t in times]
    valid_indices = [i for i, t in enumerate(parsed_times) if t <= local_now]

    if not valid_indices:
        print("⚠️ No past or current records available.")
        return

    # Choose the latest past record (most recent ≤ now)
    closest_idx = valid_indices[-1]
    closest_time = parsed_times[closest_idx]

    # Skip if already exists
    if collection.find_one({"timestamp": closest_time}):
        print(f"⏳ Data for {closest_time} already exists.")
        return

    # Create document
    record = {
        "timestamp": closest_time,
        "temperature_2m_C": hourly["temperature_2m"][closest_idx],
        "relative_humidity_2m_percent": hourly["relative_humidity_2m"][closest_idx],
        "surface_pressure_hPa": hourly["surface_pressure"][closest_idx],
        "pressure_msl_hPa": hourly["pressure_msl"][closest_idx],
        "wind_speed_10m_kmh": hourly["wind_speed_10m"][closest_idx],
        "cloud_cover_percent": hourly["cloud_cover"][closest_idx],
        "precipitation_probability_percent": hourly["precipitation_probability"][closest_idx]
    }

    collection.insert_one(record)
    print(f"✅ Inserted record for {closest_time}")

# === Loop to Run Every Hour ===
if __name__ == "__main__":
    while True:
        print(f"🔄 Running at {datetime.now(tz=tz.tzlocal()).isoformat()}")
        try:
            fetch_latest_past_hour_and_store()
        except Exception as e:
            print(f"❌ Error occurred: {e}")
        print("🕐 Waiting 1 hour...\n")
        time.sleep(3600)