from func import get_coordinates, get_weather_data
import streamlit as st
import pandas as pd
from datetime import timedelta,datetime

st.title("Real-time Weather Dashboard")
st.write("Get realtime updates to weather near you!")

city_name = st.text_input("Enter City Name")
forecast_duration = st.slider("Select forecast duration (hours)", min_value=12, max_value=48, value=24, step=12)
parameter_options = st.multiselect(
    "Choose weather parameters to display:",
    options = ["Temperature (C)", "Humidity (%)", "Wind Speed (m/s)"],
    default = ["Temperature (C)", "Humidity (%)"]
)

if st.button("Get Weather Data"):
    lat, lon = get_coordinates(city_name)
    if lat and lon:
        data = get_weather_data(lat, lon, forecast_duration)
        if data:
            times = [datetime.now() + timedelta(hours=i) for i in range(forecast_duration)]
            df = pd.DataFrame({"Time": times})

            if "Temperature (°C)" in parameter_options:
                df["Temperature (°C)"] = data['hourly']['temperature_2m'][:forecast_duration]
                st.subheader(f"Temperature Forecast")
                st.line_chart(df.set_index("Time")["Temperature (°C)"])

            if "Humidity (%)" in parameter_options:
                df["Humidity (%)"] = data['hourly']['relative_humidity_2m'][:forecast_duration]
                st.subheader(f"HumidityForecast")
                st.line_chart(df.set_index("Time")["Humidity (%)"])

            if "Wind Speed (m/s)" in parameter_options:
                df["Wind Speed (m/s)"] = data['hourly']['wind_speed_10m'][:forecast_duration]
                st.subheader(f"Wind SpeedForecast")
                st.line_chart(df.set_index("Time")["Wind Speed (m/s)"])
