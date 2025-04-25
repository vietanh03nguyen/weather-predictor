# initial_train.py

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import matplotlib.pyplot as plt

# 1. Load historical CSV file
df = pd.read_csv('open-meteo-21.00N105.88E10m.csv', skiprows=2, parse_dates=['time'])
df.set_index('time', inplace=True)

# 2. Rename columns for consistency
df = df.rename(columns={
    'relative_humidity_2m (%)': 'humidity',
    'surface_pressure (hPa)': 'pressure',
    'wind_speed_10m (km/h)': 'wind_speed',
    'cloud_cover (%)': 'cloud_cover',
    'precipitation_probability (%)': 'precip_prob',
    'temperature_2m (°C)': 'temp'
})

features = ['humidity', 'pressure', 'wind_speed', 'cloud_cover', 'precip_prob', 'temp']

# 3. Create lagged features
X_lag = df[features].shift(1).dropna()
Y = df[features].loc[X_lag.index]

# 4. Train-test split
split_date = '2025-04-17'
train_mask = X_lag.index < split_date
X_train, Y_train = X_lag[train_mask], Y[train_mask]
X_test, Y_test = X_lag[~train_mask], Y[~train_mask]

# 5. Train a model per feature
models = {}
predictions = pd.DataFrame(index=Y_test.index)

for col in features:
    model = LinearRegression()
    model.fit(X_train, Y_train[col])
    models[col] = model
    predictions[col] = model.predict(X_test)

# 6. Save the full model dictionary to a single file
joblib.dump(models, "weather_models.pkl")

# 7. Print evaluation metrics
print("📊 Evaluation metrics on test data:\n")
for col in features:
    rmse = np.sqrt(mean_squared_error(Y_test[col], predictions[col]))
    mae = mean_absolute_error(Y_test[col], predictions[col])
    print(f"{col}: RMSE = {rmse:.2f}, MAE = {mae:.2f}")

print("\n✅ Models saved to 'weather_models.pkl'")

# 8. Plot actual vs predicted for each stat
for col in features:
    plt.figure(figsize=(10, 4))
    plt.plot(Y_test.index, Y_test[col], label='Actual', linewidth=1.5)
    plt.plot(predictions.index, predictions[col], label='Predicted', linestyle='--')
    plt.title(f'Actual vs Predicted - {col}')
    plt.xlabel('Time')
    plt.ylabel(col)
    plt.legend()
    plt.tight_layout()
    plt.show()

# 9. Scatter plots
for col in features:
    plt.figure(figsize=(5, 5))
    plt.scatter(Y_test[col], predictions[col], alpha=0.5)
    plt.plot([Y_test[col].min(), Y_test[col].max()],
             [Y_test[col].min(), Y_test[col].max()], 'r--', label='Ideal')
    plt.xlabel(f'Actual {col}')
    plt.ylabel(f'Predicted {col}')
    plt.title(f'{col} Prediction Scatter Plot')
    plt.legend()
    plt.tight_layout()
    plt.show()