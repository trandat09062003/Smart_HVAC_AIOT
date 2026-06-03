# models/upgraded_model/evaluate_performance.py
"""
PHASE 4: EVALUATE AND COMPARE (RL AGENT VS BASELINE)
Evaluates the trained upgraded DQN agent against a traditional rule-based baseline controller.
Generates evaluation_results.txt and performance_comparison.png.
"""
import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import argparse
from hanoi_simulator import HanoiEnv
from train_rl import DQNAgent

def run_evaluation(episodes, weather_file, model_path, max_steps=1000):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weather_path = os.path.abspath(os.path.join(base_dir, weather_file))
    xgb_temp_path = os.path.join(base_dir, "xgb_temp.json")
    xgb_rh_path = os.path.join(base_dir, "xgb_rh.json")
    xgb_co2_path = os.path.join(base_dir, "xgb_co2.json")
    feature_names_path = os.path.join(base_dir, "feature_names.pkl")

    print("[*] Instantiating Hanoi Room Simulator for Evaluation...")
    env = HanoiEnv(
        epw_path=weather_path,
        xgb_temp_path=xgb_temp_path,
        xgb_rh_path=xgb_rh_path,
        xgb_co2_path=xgb_co2_path,
        feature_names_path=feature_names_path
    )

    state_dim = 8
    num_actions = 24
    agent = DQNAgent(state_dim, num_actions)
    agent.epsilon = 0.0 # Strict greedy evaluation
    
    if os.path.exists(model_path):
        agent.model.build((None, state_dim))
        agent.model.load_weights(model_path)
        print(f"[+] Loaded trained DQN weights from {model_path}")
    else:
        print("[!] No trained DQN weights found. Using random agent!")

    # Performance storage
    results = {
        'RL': {'energy_w': [], 'indoor_temp': [], 'indoor_rh': [], 'indoor_co2': [], 'outdoor_temp': [], 'reward': []},
        'Baseline': {'energy_w': [], 'indoor_temp': [], 'indoor_rh': [], 'indoor_co2': [], 'outdoor_temp': [], 'reward': []}
    }

    # Helper to calculate simulated power draw matching subscriber.py
    def calculate_power(ac_on, fan_on):
        standby = 5.0
        ac = 1000.0 if ac_on else 0.0
        fan = 45.0 if fan_on else 0.0
        return standby + ac + fan

    # 1. Evaluate RL Agent
    print("\n[*] Evaluating RL Agent...")
    obs = env.reset(start_step=0)
    for step in range(max_steps):
        action_idx = agent.act(obs)
        next_obs, reward, done, info = env.step(action_idx)
        
        ac_on = obs[6]
        fan_on = obs[7]
        power = calculate_power(ac_on == 1, fan_on == 1)

        results['RL']['energy_w'].append(power)
        results['RL']['indoor_temp'].append(obs[0])
        results['RL']['indoor_rh'].append(obs[1])
        results['RL']['indoor_co2'].append(obs[2])
        results['RL']['outdoor_temp'].append(obs[3])
        results['RL']['reward'].append(reward)
        obs = next_obs

    # 2. Evaluate Baseline Controller
    # Traditional Setup: AC set to 24C during work hours (8-18), Fan constantly ON during work hours (8-18).
    print("[*] Evaluating Baseline Controller...")
    obs = env.reset(start_step=0)
    for step in range(max_steps):
        hour = obs[5]
        is_office_hours = 8 <= hour < 18
        
        # Action map:
        # If office hours: AC ON @ 24C (action_idx = 5), Fan ON -> action_idx = 17 (AC 24C, Fan ON)
        # If off hours: AC OFF, Fan OFF -> action_idx = 0
        action_idx = 17 if is_office_hours else 0
        
        next_obs, reward, done, info = env.step(action_idx)
        
        ac_on = obs[6]
        fan_on = obs[7]
        power = calculate_power(ac_on == 1, fan_on == 1)

        results['Baseline']['energy_w'].append(power)
        results['Baseline']['indoor_temp'].append(obs[0])
        results['Baseline']['indoor_rh'].append(obs[1])
        results['Baseline']['indoor_co2'].append(obs[2])
        results['Baseline']['outdoor_temp'].append(obs[3])
        results['Baseline']['reward'].append(reward)
        obs = next_obs

    # Calculate metrics
    rl_avg_power = np.mean(results['RL']['energy_w'])
    bs_avg_power = np.mean(results['Baseline']['energy_w'])
    savings = (bs_avg_power - rl_avg_power) / bs_avg_power * 100.0

    rl_co2_exceed = sum(1 for c in results['RL']['indoor_co2'] if c > 1000.0) / max_steps * 100.0
    bs_co2_exceed = sum(1 for c in results['Baseline']['indoor_co2'] if c > 1000.0) / max_steps * 100.0

    report = f"""==================================================
EVALUATION REPORT: MULTI-OBJECTIVE UPGRADED AI MODEL
Hanoi Climate Scenario (EPW Weather)
==================================================
Average Power Demand (RL Agent):       {rl_avg_power:.2f} W
Average Power Demand (Baseline):       {bs_avg_power:.2f} W
Energy Savings via RL Agent:           {savings:.2f} %
--------------------------------------------------
Air Quality Comfort (CO2 > 1000 ppm):
  - RL Agent:                          {rl_co2_exceed:.2f} % of hours
  - Baseline:                          {bs_co2_exceed:.2f} % of hours
--------------------------------------------------
Overall Comfort Reward (higher is better):
  - RL Agent Cumulative Reward:        {sum(results['RL']['reward']):.2f}
  - Baseline Cumulative Reward:        {sum(results['Baseline']['reward']):.2f}
==================================================
"""
    print(report)

    # Save report
    report_path = os.path.join(base_dir, "evaluation_results.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[+] Saved evaluation report to: {report_path}")

    # Plotting comparison
    print("[*] Generating comparison plots...")
    slice_idx = 168 # Show a full week (168 hours)
    plt.figure(figsize=(15, 12))

    # Temperature Plot
    plt.subplot(4, 1, 1)
    plt.plot(results['RL']['indoor_temp'][:slice_idx], label='RL Indoor Temp', color='orange', linewidth=2)
    plt.plot(results['Baseline']['indoor_temp'][:slice_idx], label='Baseline Indoor Temp', color='red', linestyle='--')
    plt.plot(results['RL']['outdoor_temp'][:slice_idx], label='Outdoor Temp', color='gray', alpha=0.5)
    plt.axhline(22, color='green', linestyle=':', alpha=0.5, label='Comfort Zone (22-26C)')
    plt.axhline(26, color='green', linestyle=':')
    plt.ylabel('Temperature (°C)')
    plt.title('Hanoi Upgraded HVAC Control: RL vs Baseline Performance (1 Week)')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    # Relative Humidity Plot
    plt.subplot(4, 1, 2)
    plt.plot(results['RL']['indoor_rh'][:slice_idx], label='RL Indoor Humidity', color='blue', linewidth=2)
    plt.plot(results['Baseline']['indoor_rh'][:slice_idx], label='Baseline Indoor Humidity', color='cyan', linestyle='--')
    plt.axhline(40, color='green', linestyle=':', alpha=0.5, label='Comfort Zone (40-65%)')
    plt.axhline(65, color='green', linestyle=':')
    plt.ylabel('Humidity (% RH)')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    # CO2 Plot
    plt.subplot(4, 1, 3)
    plt.plot(results['RL']['indoor_co2'][:slice_idx], label='RL Indoor CO2', color='purple', linewidth=2)
    plt.plot(results['Baseline']['indoor_co2'][:slice_idx], label='Baseline Indoor CO2', color='magenta', linestyle='--')
    plt.axhline(1000, color='red', linestyle=':', alpha=0.7, label='Safety Threshold (1000 ppm)')
    plt.ylabel('CO2 (ppm)')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    # Power Consumption Plot
    plt.subplot(4, 1, 4)
    plt.plot(results['RL']['energy_w'][:slice_idx], label='RL Power', color='green', linewidth=2)
    plt.plot(results['Baseline']['energy_w'][:slice_idx], label='Baseline Power', color='brown', linestyle='--')
    plt.ylabel('Power Draw (W)')
    plt.xlabel('Simulation Hour')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join(base_dir, "performance_comparison.png")
    plt.savefig(plot_path, dpi=150)
    print(f"[+] Saved comparison plot to: {plot_path}")
    print("[*] Completed Phase 4 successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--weather', type=str, default='../temperature_model/weather/VNM_NVN_Hanoi-Noi.Bai.Intl.AP.488200_TMYx.2009-2023.epw')
    parser.add_argument('--model', type=str, default='models/dqn_hvac_upgraded.weights.h5')
    args = parser.parse_args()

    run_evaluation(1, args.weather, args.model)
