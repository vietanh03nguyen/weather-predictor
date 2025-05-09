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
import pytz # Import pytz for timezone handling

# -------------------- Setup --------------------

st.set_page_config(page_title="🌦️ Weather Forecast", layout="centered")

# Auto-refresh every 60 seconds
st_autorefresh(interval=60 * 1000, key="refresh")

# Load the trained model components
try:
    with open("./forecast_objs.pkl", 'rb') as f:
        loaded_models = joblib.load(f)
    trend_models = loaded_models.get('trend_models')
    global_models = loaded_models.get('global_models')
    # We don't need history_df from the pickle for the app's logic,
    # but we will fetch recent data from MongoDB for context and plotting.

    if not trend_models or not global_models:
         st.error("⚠️ Could not load trend_models or global_models from pickle file.")
         st.stop()

except FileNotFoundError:
    st.error("⚠️ Model file 'forecast_objs.pkl' not found. Please run the forecasting script first.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Error loading model file: {e}")
    st.stop()


# Define the list of weather features that the models predict (using the renamed column names)
# This list should match the variables used in your forecasting script's models
# Ensure these keys exist in trend_models or global_models after loading
expected_features = ['temperature', 'pressure', 'rh', 'pp', 'cloud_cover', 'wind_speed']
# Add dew_point if it's expected and modeled
if 'dew_point' in trend_models or ('dew_point' in global_models and global_models['dew_point'] is not None):
     expected_features.append('dew_point')

# Filter features based on what models were actually loaded
features = [f for f in expected_features if f in trend_models or (f in global_models and global_models[f] is not None)]

if not features:
     st.error("⚠️ No valid weather models loaded. Cannot proceed with forecasting.")
     st.stop()


# MongoDB setup
MONGO_URI = "mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority"
try:
    client = MongoClient(MONGO_URI)
    collection = client["weather_db"]["realtime_weather"]
    # Check if connection is successful
    client.admin.command('ping')
except Exception as e:
    st.error(f"⚠️ Could not connect to MongoDB: {e}")
    st.stop()


# Define the column mapping from MongoDB field names to internal names
# This must match the mapping used in your data pulling script and forecasting script
col_map = {
    'timestamp': 'time',
    'temperature_2m_C': 'temperature',
    'surface_pressure_hPa': 'pressure',
    'pressure_msl_hPa': 'pressure_msl', # Keep this mapping if the field exists
    'relative_humidity_2m_percent': 'rh',
    'precipitation_probability_percent': 'pp',
    'cloud_cover_percent': 'cloud_cover',
    'wind_speed_10m_kmh': 'wind_speed',
    # Add dew point mapping if available in your MongoDB data
    # 'dew_point_field_name_in_mongo': 'dew_point'
}

# Fetch recent historical data from MongoDB (e.g., last 7 days)
# This data is used for plotting historical context and determining the latest timestamp
try:
    # Fetch data from the last 7 days
    time_threshold = datetime.utcnow() - timedelta(days=7)
    # Query for documents with timestamp greater than the threshold
    recent_data_cursor = collection.find({"timestamp": {"$gte": time_threshold}}).sort("timestamp", 1)

    # Convert MongoDB cursor to pandas DataFrame
    df_hist = pd.DataFrame(list(recent_data_cursor))

    if df_hist.empty:
        st.warning("⚠️ No recent historical data found in MongoDB for the last 7 days.")
        # Attempt to fetch any data if recent is empty
        any_data_cursor = collection.find().sort("timestamp", 1).limit(100) # Fetch up to 100 records
        df_hist = pd.DataFrame(list(any_data_cursor))
        if df_hist.empty:
             st.error("⚠️ No historical data found in MongoDB.")
             st.stop()
        else:
             st.info(f"Displaying history from the latest {len(df_hist)} records available.")


    # Drop the MongoDB default _id column if it exists
    if '_id' in df_hist.columns:
        df_hist.drop(columns=['_id'], inplace=True)

    # Rename columns based on the mapping
    df_hist.rename(columns={k: v for k,v in col_map.items() if k in df_hist.columns}, inplace=True)

    # Ensure the 'time' column exists and is in the correct format
    if 'time' not in df_hist.columns:
        st.error("Error: 'time' column not found in historical data after renaming.")
        st.stop()

    df_hist['time'] = pd.to_datetime(df_hist['time'], errors='coerce')
    # --- FIX: Localize the timestamp to UTC after converting to datetime ---
    # Assumes the timestamps fetched from MongoDB are in UTC (as stored by the data pulling script)
    df_hist['time'] = df_hist['time'].dt.tz_localize('UTC')
    # --- End FIX ---
    df_hist.sort_values('time', inplace=True)
    df_hist.dropna(subset=['time'], inplace=True) # Ensure time column has no NaNs
    df_hist['ord'] = df_hist['time'].dt.date.map(lambda d: d.toordinal())

    # Ensure required columns for plotting and potential base forecasts exist
    required_plot_cols = [col for col in features if col in df_hist.columns]
    if not required_plot_cols:
        st.warning("⚠️ None of the forecasted features are available in the historical data for plotting.")

except Exception as e:
    st.error(f"⚠️ Error fetching or processing historical data from MongoDB: {e}")
    st.stop()


# Get the latest timestamp from the historical data
latest_hist_time = df_hist['time'].max()
if pd.isna(latest_hist_time):
    st.error("⚠️ Could not determine the latest historical timestamp from MongoDB data.")
    st.stop()


# Fetch current apparent temperature from Open-Meteo API for display
lat, lon = 21.0285, 105.8542 # Use the same coordinates as data fetching
open_meteo_current_url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}&current=apparent_temperature&timezone=Asia%2FBangkok"
)

current_apparent_temp = None
try:
    response = requests.get(open_meteo_current_url)
    response.raise_for_status()
    current_apparent_temp = response.json()["current"]["apparent_temperature"]
except Exception as e:
    st.warning(f"⚠️ Could not fetch current apparent temperature from Open-Meteo API: {e}")


# -------------------- Forecasting Logic (Adapted from Forecasting Script) --------------------

# Need to adapt forecast_at and batch_forecast to use the loaded models
# These functions rely on the structure of trend_models and global_models

def forecast_at_streamlit(col, ts: datetime, trend_models, global_models):
    """Forecast single variable col at timestamp ts using loaded models."""
    # Check if the column is one we intended to model and if trend models were built
    # Use 'features' list which contains columns with loaded models
    if col not in features or col not in trend_models or trend_models[col] is None:
        # print(f"Warning: Trend models not available or built for {col}. Cannot forecast.")
        return np.nan # Cannot forecast if models are not available or column not expected

    hr = ts.hour
    # trend part
    model = trend_models[col].get(hr)
    ord_val = ts.date().toordinal()
    trend = np.nan
    if model:
        try:
            trend = model.predict(pd.DataFrame([[ord_val]], columns=['ord']))[0]
        except Exception as e:
             # print(f"Error during trend prediction for {col} at {ts.isoformat()}: {e}")
             trend = np.nan


    # direct return for base vars (temperature and pressure)
    if col in ['temperature','pressure']:
        return trend

    # For derived variables, check if global models exist
    if col not in global_models or global_models[col] is None:
        # print(f"Warning: Global models not available for {col}. Returning only trend if available.")
        return trend if not np.isnan(trend) else np.nan # Return trend if available, otherwise NaN

    # recursive forecasts for temp & pressure
    # Call forecast_at_streamlit recursively
    temp = forecast_at_streamlit('temperature', ts, trend_models, global_models)
    press = forecast_at_streamlit('pressure', ts, trend_models, global_models)

    # Check if base forecasts are valid
    if np.isnan(temp) or np.isnan(press):
        # print(f"Warning: Base forecasts (temp/pressure) are NaN for {col} at {ts.isoformat()}. Cannot use global models.")
        return trend if not np.isnan(trend) else np.nan # Return trend if available, otherwise NaN


    # global regressions
    tm = global_models[col]['temp_model']
    pm = global_models[col]['press_model']

    from_temp = np.nan
    try:
        # Ensure the input to predict is a DataFrame with the correct column name
        from_temp = tm.predict(pd.DataFrame([[temp]], columns=['temperature']))[0]
    except Exception as e:
         # print(f"Error during temperature regression prediction for {col} at {ts.isoformat()}: {e}")
         pass # Suppress errors for smoother app experience

    from_press = np.nan
    try:
        # Ensure the input to predict is a DataFrame with the correct column name
        from_press = pm.predict(pd.DataFrame([[press]], columns=['pressure']))[0]
    except Exception as e:
         # print(f"Error during pressure regression prediction for {col} at {ts.isoformat()}: {e}")
         pass # Suppress errors for smoother app experience


    # geometric mean, consider only valid components
    vals = np.array([v for v in [trend, from_temp, from_press] if not np.isnan(v)])

    if len(vals) == 0:
        return np.nan # No valid components to calculate mean

    # Handle cases where values might be zero or negative before taking log for geometric mean
    eps = 1e-9 # Use a smaller epsilon
    vals_positive = vals + eps
    vals_positive[vals_positive <= 0] = eps # Ensure strictly positive before log

    return float(np.exp(np.nanmean(np.log(vals_positive))))


def batch_forecast_streamlit(start_ts: datetime, hours_ahead: int, trend_models, global_models, features):
    """Generates batch forecasts starting from start_ts for hours_ahead."""
    forecast_times = [start_ts + timedelta(hours=i) for i in range(1, hours_ahead + 1)] # Forecast starts AFTER start_ts

    # Ensure we only attempt to forecast columns for which trend models were built
    cols_to_forecast = [c for c in features if c in trend_models and trend_models[c] is not None]
    # Add derived variables that have global models, even if trend model wasn't built for all hours
    cols_to_forecast.extend([c for c in features if c not in cols_to_forecast and c in global_models and global_models[c] is not None])
    # Ensure unique and maintain order if possible, or just use the 'features' order
    cols_to_forecast = [c for c in features if c in cols_to_forecast]


    results = {c: [] for c in cols_to_forecast}

    if not cols_to_forecast:
        st.warning("No valid columns to forecast after model loading.")
        return pd.DataFrame(index=forecast_times) # Return empty DataFrame

    for ts in forecast_times:
        for col in cols_to_forecast:
            results[col].append(forecast_at_streamlit(col, ts, trend_models, global_models))

    return pd.DataFrame(results, index=forecast_times)


# -------------------- UI --------------------

st.title("🌤️ Real-Time Weather Forecast")

# Local time (Hanoi)
hanoi_tz = ZoneInfo("Asia/Ho_Chi_Minh")
local_time_now = datetime.now(hanoi_tz).replace(second=0, microsecond=0)
st.subheader(f"📅 Hanoi Local Time: {local_time_now.strftime('%Y-%m-%d %H:%M')}")

# -------------------- Current Weather --------------------
st.markdown("---")
st.markdown("### 🌡️ Current Weather (Latest from MongoDB)")

if not df_hist.empty:
    if current_apparent_temp is not None:
         st.metric("Feels Like (°C) (Live API)", f"{current_apparent_temp:.2f}")
    latest_record = df_hist.iloc[-1]
    # The timestamp is now timezone-aware (UTC) after tz_localize, so astimezone works
    st.write(f"Data timestamp: {latest_record['time'].astimezone(hanoi_tz).strftime('%Y-%m-%d %H:%M')}")

    col1, col2 = st.columns(2)
    with col1:
        # Use .get() for safety in case a column is missing in the latest record
        st.metric("Temperature (°C)", f"{latest_record.get('temperature', np.nan):.2f}" if pd.notna(latest_record.get('temperature')) else "N/A")
        st.metric("Humidity (%)", f"{latest_record.get('rh', np.nan):.2f}" if pd.notna(latest_record.get('rh')) else "N/A")
        st.metric("Cloud Cover (%)", f"{latest_record.get('cloud_cover', np.nan):.2f}" if pd.notna(latest_record.get('cloud_cover')) else "N/A")

    with col2:
        st.metric("Wind Speed (km/h)", f"{latest_record.get('wind_speed', np.nan):.2f}" if pd.notna(latest_record.get('wind_speed')) else "N/A")
        st.metric("Precipitation Probability (%)", f"{latest_record.get('pp', np.nan):.2f}" if pd.notna(latest_record.get('pp')) else "N/A")
        st.metric("Surface Pressure (hPa)", f"{latest_record.get('pressure', np.nan):.2f}" if pd.notna(latest_record.get('pressure')) else "N/A")

    # Display apparent temperature if fetched
    

else:
    st.info("No historical data available to display current weather.")


# Slider for prediction horizon
hours_ahead = st.slider("⏱️ Forecast range (hours)", min_value=1, max_value=24, value=12) # Max 7 days (168 hours)

# -------------------- Prediction --------------------

st.markdown("---")

if not df_hist.empty:
    # Start forecasting from the latest historical timestamp + 1 hour
    forecast_start_time = latest_hist_time
    # Generate batch forecast
    forecast_df = batch_forecast_streamlit(forecast_start_time, hours_ahead, trend_models, global_models, features)

    if not forecast_df.empty:
        # Convert forecast index to Hanoi timezone for display
        forecast_df.index = forecast_df.index.tz_convert(hanoi_tz)

        

        # Display forecast charts
        st.markdown("### 📈 Forecast Charts")
        # Use only columns that actually have forecast data (not all NaNs)
        plottable_features = [col for col in forecast_df.columns if not forecast_df[col].isnull().all()]

        if plottable_features:
            tabs = st.tabs([f"{feature.replace('_', ' ').title()}" for feature in plottable_features])

            for i, feature in enumerate(plottable_features):
                with tabs[i]:
                    fig, ax = plt.subplots(figsize=(10, 4)) # Increased figure size
                    # Plot historical data for context (last few points)
                    if feature in df_hist.columns and not df_hist[feature].isnull().all():
                        # Plot last 24 hours of historical data if available
                        hist_plot_start = latest_hist_time - timedelta(hours=24)
                        df_hist_plot = df_hist[df_hist['time'] > hist_plot_start].copy()
                        # Convert historical time to Hanoi timezone for plotting
                        df_hist_plot['time'] = df_hist_plot['time'].dt.tz_convert(hanoi_tz)
                        ax.plot(df_hist_plot['time'], df_hist_plot[feature], label='History', marker='.', linestyle='-', color='tab:orange', alpha=0.7)


                    ax.plot(forecast_df.index, forecast_df[feature], label='Forecast', marker='o', linestyle='--', color='tab:blue')

                    ax.set_title(f"{feature.replace('_', ' ').title()} Forecast")
                    ax.set_xlabel("Time")
                    # Add units to ylabel based on feature name
                    ylabel_text = feature.replace('_', ' ').title()
                    if feature == 'temperature' or feature == 'dew_point':
                        ylabel_text += ' (°C)'
                    elif feature == 'pressure' or feature == 'pressure_msl':
                         ylabel_text += ' (hPa)'
                    elif feature == 'rh' or feature == 'cloud_cover' or feature == 'pp':
                         ylabel_text += ' (%)'
                    elif feature == 'wind_speed':
                         ylabel_text += ' (km/h)'
                    ax.set_ylabel(ylabel_text)

                    ax.legend()
                    ax.grid(True)
                    plt.xticks(rotation=45, ha='right') # Rotate x-axis labels
                    plt.tight_layout() # Adjust layout to prevent labels overlapping
                    st.pyplot(fig)
                    plt.close(fig) # Close the figure to free memory
        else:
             st.info("No forecast data available to plot.")
        
        # Display forecast table
        st.markdown("### 🔮 Predicted Weather")

        st.dataframe(forecast_df.round(2))

    else:
        st.info("No forecast generated. Check historical data and model loading.")
else:
    st.info("No historical data available to generate forecast.")
