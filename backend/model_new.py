import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression
import pytz

# ----------------- Configuration -----------------
LAT = 21.00
LON = 105.88
TIMEZONE = "Asia/Bangkok"
MONGO_URI = "mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority"

# ----------------- MongoDB Setup -----------------
client = MongoClient(MONGO_URI)
db = client["weather_db"]
realtime_col = db["realtime_weather"]
predict_col = db["predict_weather"]

# ----------------- Step 1: Fetch Current Data -----------------
def fetch_current_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": ["temperature_2m", "surface_pressure"],
        "timezone": TIMEZONE
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()["current"]
        now = datetime.now(pytz.timezone(TIMEZONE))
        return {
            "timestamp": now,
            "temperature": data.get("temperature_2m"),
            "pressure": data.get("surface_pressure")
        }
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

# ----------------- Step 2: Store in MongoDB -----------------
def store_realtime_weather(data):
    if data:
        realtime_col.insert_one(data)
        print("✅ Current weather stored.")

# ----------------- Step 3: Train Linear Models -----------------
def train_models():
    df = pd.DataFrame(list(realtime_col.find()))
    if len(df) < 10:
        print("Not enough data to train.")
        return None

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values("timestamp", inplace=True)
    df['ordinal'] = df['timestamp'].map(lambda x: x.toordinal() + x.hour / 24.0)

    X = df[['ordinal']]

    models = {}
    for target in ['temperature', 'pressure']:
        y = df[target]
        model = LinearRegression().fit(X, y)
        models[target] = model
    return models

# ----------------- Step 4: Predict Next 48 Hours -----------------
def generate_predictions(models):
    now = datetime.now(pytz.timezone(TIMEZONE))
    future_times = [now + timedelta(hours=i) for i in range(1, 49)]
    predictions = []

    for t in future_times:
        ordinal = t.toordinal() + t.hour / 24.0
        record = {
            "timestamp": t,
            "temperature": round(models['temperature'].predict([[ordinal]])[0], 2),
            "pressure": round(models['pressure'].predict([[ordinal]])[0], 2)
        }
        predictions.append(record)
    
    return predictions

# ----------------- Step 5: Store Predictions -----------------
def store_predictions(predictions):
    predict_col.delete_many({})  # Clear old predictions
    predict_col.insert_many(predictions)
    print("✅ 48-hour predictions stored in MongoDB.")

# ----------------- Main -----------------
if __name__ == "__main__":
    current_data = fetch_current_weather()
    store_realtime_weather(current_data)
    models = train_models()
    if models:
        preds = generate_predictions(models)
        store_predictions(preds)
