# models/upgraded_model/train_surrogate.py
"""
PHASE 1: TRAIN HYBRID SURROGATE MODELS (XGBOOST) WITH ACTUAL CO2 DATA
Trains:
  1. Temperature Surrogate (xgb_temp.json) using Cleaned_data_encode.csv (Vietnam telemetry).
  2. Humidity Surrogate (xgb_rh.json) using Cleaned_data_encode.csv (Vietnam telemetry).
  3. CO2 Surrogate (xgb_co2.json) using the famous UCI Occupancy Detection Dataset with actual CO2 telemetry.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# Data paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMP_DIR = os.path.abspath(os.path.join(BASE_DIR, "../temperature_model"))

XGB_ENCODE_FILE = os.path.join(TEMP_DIR, "Cleaned_data_encode.csv")
UCI_DATA_FILE = os.path.join(BASE_DIR, "data/uci_occupancy.csv")

print("[*] Redoing Phase 1 with complete and reputable datasets...")

# ----------------------------------------------------------------------
# 1. Train Temperature & Humidity Emulators (Vietnam Climate)
# ----------------------------------------------------------------------
if not os.path.exists(XGB_ENCODE_FILE):
    raise FileNotFoundError(f"Cleaned_data_encode.csv not found at {XGB_ENCODE_FILE}!")

data_vn = pd.read_csv(XGB_ENCODE_FILE)

# Select numeric features for Temperature & Humidity surrogates
features_to_drop = ['Next_Indoor_Temp', 'Next_Indoor_RH', 'Date_Time', 'Study_ID', 'Differ_Indoor_Temp', 'ID']
data_vn['Differ_Indoor_RH'] = data_vn['Next_Indoor_RH'] - data_vn['Indoor_RH']

X_vn = data_vn.drop(features_to_drop + ['Next_Outdoor_Temp', 'Next_Outdoor_RH', 'Differ_Indoor_RH'], axis=1, errors='ignore')

# 1.1 Temperature Surrogate
y_temp = data_vn['Differ_Indoor_Temp']
X_train_t, X_test_t, y_train_t, y_test_t = train_test_split(X_vn, y_temp, test_size=0.2, random_state=2022)

print("\n[*] Training Temperature Emulator (XGBoost Temp Model)...")
model_xgb_temp = xgb.XGBRegressor(
    random_state=2000,
    verbosity=0,
    n_jobs=-1,
    max_depth=5,
    learning_rate=0.23,
    n_estimators=300
)
model_xgb_temp.fit(X_train_t, y_train_t)
y_pred_t = model_xgb_temp.predict(X_test_t)
print(f"  -> Temperature Model MSE: {mean_squared_error(y_test_t, y_pred_t):.4f}, R2 Score: {r2_score(y_test_t, y_pred_t):.4f}")

# 1.2 Humidity Surrogate
y_rh = data_vn['Differ_Indoor_RH']
X_train_h, X_test_h, y_train_h, y_test_h = train_test_split(X_vn, y_rh, test_size=0.2, random_state=2022)

print("[*] Training Humidity Emulator (XGBoost Humidity Model)...")
model_xgb_rh = xgb.XGBRegressor(
    random_state=2000,
    verbosity=0,
    n_jobs=-1,
    max_depth=5,
    learning_rate=0.23,
    n_estimators=300
)
model_xgb_rh.fit(X_train_h, y_train_h)
y_pred_h = model_xgb_rh.predict(X_test_h)
print(f"  -> Humidity Model MSE: {mean_squared_error(y_test_h, y_pred_h):.4f}, R2 Score: {r2_score(y_test_h, y_pred_h):.4f}")


# ----------------------------------------------------------------------
# 2. Train CO2 Accumulation Emulator (UCI Occupancy Dataset)
# ----------------------------------------------------------------------
if not os.path.exists(UCI_DATA_FILE):
    raise FileNotFoundError(f"UCI occupancy data not found at {UCI_DATA_FILE}!")

# Read UCI data
data_uci = pd.read_csv(UCI_DATA_FILE)

# Prepare CO2 features
# We predict Differ_CO2 = Next_CO2 - CO2
# Shift CO2 to get next step CO2
data_uci['Next_CO2'] = data_uci['CO2'].shift(-1)
data_uci['Differ_CO2'] = data_uci['Next_CO2'] - data_uci['CO2']
data_uci = data_uci.dropna()

# Inputs for CO2: ['CO2', 'Temperature', 'Humidity', 'Occupancy']
X_co2 = data_uci[['CO2', 'Temperature', 'Humidity', 'Occupancy']].values
y_co2 = data_uci['Differ_CO2'].values

X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_co2, y_co2, test_size=0.2, random_state=2022)

print("\n[*] Training CO2 Generation & Decay Emulator (XGBoost CO2 Model from UCI)...")
model_xgb_co2 = xgb.XGBRegressor(
    random_state=2000,
    verbosity=0,
    n_jobs=-1,
    max_depth=5,
    learning_rate=0.2,
    n_estimators=200
)
model_xgb_co2.fit(X_train_c, y_train_c)
y_pred_c = model_xgb_co2.predict(X_test_c)
print(f"  -> CO2 Model MSE: {mean_squared_error(y_test_c, y_pred_c):.4f}, R2 Score: {r2_score(y_test_c, y_pred_c):.4f}")


# ----------------------------------------------------------------------
# 3. Export Models & Features
# ----------------------------------------------------------------------
xgb_temp_path = os.path.join(BASE_DIR, "xgb_temp.json")
xgb_rh_path = os.path.join(BASE_DIR, "xgb_rh.json")
xgb_co2_path = os.path.join(BASE_DIR, "xgb_co2.json")
features_path = os.path.join(BASE_DIR, "feature_names.pkl")

model_xgb_temp.save_model(xgb_temp_path)
model_xgb_rh.save_model(xgb_rh_path)
model_xgb_co2.save_model(xgb_co2_path)

with open(features_path, 'wb') as f:
    pickle.dump(list(X_vn.columns), f)

print(f"\n[+] Hybrid surrogate models trained and saved successfully!")
print(f"  - Temperature Emulator: {xgb_temp_path}")
print(f"  - Humidity Emulator:    {xgb_rh_path}")
print(f"  - CO2 Emulator (UCI):   {xgb_co2_path}")
print("[*] Redone Phase 1 successfully.")
