import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
from dateutil import parser, tz
import time

# === 1. MongoDB Setup ===
client = MongoClient("mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority")
db = client["weather_db"]
collection = db["realtime_weather"]

# === Open-Meteo API Setup ===
latitude = 21.0285
longitude = 105.8542
timezone = "auto"
weather_params = [
    "temperature_2m", "relative_humidity_2m", "surface_pressure",
    "pressure_msl", "wind_speed_10m", "cloud_cover", "precipitation_probability"
]

def fetch_last_7d_until_current_hour_and_store():
    try:
        time_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m&timezone={timezone}"
        time_response = requests.get(time_url)
        time_response.raise_for_status()
        api_now_str = time_response.json().get("current", {}).get("time")
        now_in_api_tz = parser.isoparse(api_now_str) if api_now_str else datetime.now(tz=tz.tzlocal())
    except Exception as e:
        print(f"❌ Time fetch failed, using local time: {e}")
        now_in_api_tz = datetime.now(tz=tz.tzlocal())

    start_date_str = (now_in_api_tz - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date_str = now_in_api_tz.strftime("%Y-%m-%d")

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly={','.join(weather_params)}"
        f"&timezone={timezone}"
        f"&start_date={start_date_str}&end_date={end_date_str}"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        hourly_data = data.get("hourly", {})
        times = hourly_data.get("time", [])
    except Exception as e:
        print(f"❌ Failed to fetch weather data: {e}")
        return

    if not times:
        print("⚠️ No weather data received.")
        return

    inserted = 0
    for idx, t_str in enumerate(times):
        try:
            ts_local = parser.isoparse(t_str)
            if ts_local > now_in_api_tz:
                continue

            ts_utc = ts_local.astimezone(tz.tzutc())
            if collection.find_one({"timestamp": ts_utc}):
                continue

            record = {
                "timestamp": ts_utc,
                "temperature_2m_C": hourly_data["temperature_2m"][idx],
                "relative_humidity_2m_percent": hourly_data["relative_humidity_2m"][idx],
                "surface_pressure_hPa": hourly_data["surface_pressure"][idx],
                "pressure_msl_hPa": hourly_data["pressure_msl"][idx],
                "wind_speed_10m_kmh": hourly_data["wind_speed_10m"][idx],
                "cloud_cover_percent": hourly_data["cloud_cover"][idx],
                "precipitation_probability_percent": hourly_data["precipitation_probability"][idx]
            }
            collection.insert_one(record)
            inserted += 1
        except Exception as e:
            print(f"⚠️ Skipped timestamp {t_str}: {e}")

    print(f"✅ Inserted {inserted} records from last 7 days up to current hour.")

# === Run in Infinite Loop ===
if __name__ == "__main__":
    while True:
        print(f"\n🔄 Fetching at {datetime.now(tz=tz.tzlocal()).isoformat()}")
        try:
            fetch_last_7d_until_current_hour_and_store()
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        print("🕐 Waiting 1 hour...\n")
        time.sleep(3600)
