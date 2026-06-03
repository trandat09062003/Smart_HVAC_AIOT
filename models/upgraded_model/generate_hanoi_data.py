# models/upgraded_model/generate_hanoi_data.py
"""
PHASE 2: GENERATE HANOI SIMULATION EXPERIENCE DATA
This script parses the Hanoi EPW weather file, instantiates the dynamic room emulator,
and runs a simulation to generate transition experience data (Saved to Sinergym_Transition_Data.csv).
"""
import pandas as pd
import numpy as np
import os
import argparse
from hanoi_simulator import HanoiEnv

def main():
    parser = argparse.ArgumentParser(description="Generate sequence data for Hanoi climate")
    parser.add_argument('--weather', type=str, default='../temperature_model/weather/VNM_NVN_Hanoi-Noi.Bai.Intl.AP.488200_TMYx.2009-2023.epw', help='Path to EPW weather file')
    parser.add_argument('--steps', type=int, default=5000, help='Number of simulation steps to run')
    args = parser.parse_args()

    # Resolve paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weather_path = os.path.abspath(os.path.join(base_dir, args.weather))
    xgb_temp_path = os.path.join(base_dir, "xgb_temp.json")
    xgb_rh_path = os.path.join(base_dir, "xgb_rh.json")
    xgb_co2_path = os.path.join(base_dir, "xgb_co2.json")
    feature_names_path = os.path.join(base_dir, "feature_names.pkl")

    print("[*] Instantiating Hanoi Room Simulator with Hybrid CO2 Model...")
    print(f"  - Weather EPW: {weather_path}")
    
    if not os.path.exists(weather_path):
        raise FileNotFoundError(f"Weather file not found at: {weather_path}")

    env = HanoiEnv(
        epw_path=weather_path,
        xgb_temp_path=xgb_temp_path,
        xgb_rh_path=xgb_rh_path,
        xgb_co2_path=xgb_co2_path,
        feature_names_path=feature_names_path
    )

    print(f"[*] Simulating {args.steps} steps under Hanoi Climate...")
    
    obs = env.reset()
    transition_data = []

    for step in range(args.steps):
        action = np.random.randint(24)
        state_features = obs.copy()
        next_obs, reward, done, info = env.step(action)
        
        row = {
            "Step": step,
            "Action_Index": action,
            "Indoor_Temp": state_features[0],
            "Indoor_RH": state_features[1],
            "Indoor_CO2": state_features[2],
            "Outdoor_Temp": state_features[3],
            "Outdoor_RH": state_features[4],
            "Hour": state_features[5],
            "AC_Status": state_features[6],
            "Fan_Status": state_features[7],
            "Next_Indoor_Temp": next_obs[0],
            "Next_Indoor_RH": next_obs[1],
            "Next_Indoor_CO2": next_obs[2],
            "Reward": reward
        }
        transition_data.append(row)
        obs = next_obs
        
        if (step + 1) % 1000 == 0:
            print(f"  ... Simulated {step + 1}/{args.steps} steps")

    # Write to CSV
    output_filename = os.path.join(base_dir, "Sinergym_Transition_Data.csv")
    df = pd.DataFrame(transition_data)
    df.to_csv(output_filename, index=False)
    print(f"\n[+] Hanoi experience data generation complete!")
    print(f"  - Saved {len(df)} transition rows to: {output_filename}")
    print("[*] Completed Phase 2 successfully.")

if __name__ == "__main__":
    main()
