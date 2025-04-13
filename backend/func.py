import requests
import streamlit as st

def get_coordinates(city_name):
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1&email=lightning064@gmail.com"
    # headers = {"User-Agent": "WeatherDashboardApp/1.0 (vietanh03nguyen@gmail.com)"}
    response = requests.get(url)
    
    if response.status_code == 200:
        location_data = response.json()
        if location_data:
            location = location_data[0]
            return float(location['lat']), float(location['lon'])
        else:
            st.warning("City not found.")
            return None, None
        
    else:
        st.error(f"API request failed with status code: {response.status_code}: {response.text}")
        return None, None
    
def get_weather_data(lat, lon, hours):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&forecast_days=2"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to retrieve weather data.")
        return None