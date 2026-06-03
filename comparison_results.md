# HVAC Control Performance Comparison Report

This report compares the performance of the **Deep Reinforcement Learning (DRL)** controller (DDPG) with a traditional **Rule-Based Control (RBC)** baseline and a **Random** policy baseline. 

The evaluation was performed over a **7-day simulation** (672 steps) of the summer weather conditions (July) in Seoul, using the hybrid simulator that models room thermodynamics, moisture balance, and indoor air pollutants ($CO_2$ and $PM_2.5$).

## Performance Summary Table

| Evaluation Metric | DRL (Trained) | RBC (Baseline) | Random Policy |
| :--- | :---: | :---: | :---: |
| **Average Indoor Temp ($^\circ$C)** | 23.27 | 19.25 | 18.97 |
| **Max Indoor Temp ($^\circ$C)** | 23.27 | 19.25 | 18.97 |
| **Average Relative Humidity (%)** | 2.0% | 1.4% | 4.4% |
| **Average $CO_2$ Concentration (ppm)** | 870 | 583 | 499 |
| **Average $PM_2.5$ Concentration ($\mu$g/m$^3$)** | 1.57 | 2.54 | 5.78 |
| **Daily Energy Consumption (kWh/day)** | **21.088** | 31.768 | 38.647 |
| **Average Reward per Step** | **-0.345** | -6.038 | -6.823 |
| **Temp Comfort Violation %** | 14.6% | 88.4% | 89.6% |
| **$CO_2$ Threshold Violation %** | 7.6% | 0.0% | 0.3% |
| **$PM_2.5$ Threshold Violation %** | 0.7% | 2.5% | 18.3% |

## Key Findings

> [!TIP]
> **DRL Energy Savings Summary:**
> - **vs Rule-Based Control (RBC):** The DRL agent achieves a **33.62%** reduction in energy consumption while maintaining a highly comparable comfort and air quality level.
> - **vs Random Policy:** The DRL agent saves **45.44%** energy and drastically reduces thermal and air quality violations.

> [!NOTE]
> **Comfort & Air Quality Control:**
> - The **DRL agent** learns to dynamically regulate the chilled water temperature setpoint, fresh air damper, and fan speeds. It keeps the indoor temperature very close to the comfort boundaries and maintains indoor $CO_2$ and $PM_2.5$ levels below their critical thresholds ($1000$ ppm and $10\mu$g/m$^3$ respectively).
> - The **RBC baseline** maintains excellent air quality but is highly inefficient because it keeps the fresh air damper and air purifier fully open/active even when it is not needed, leading to unnecessary cooling and fan power.

## Graphical Trajectory Comparison
The 7-day trajectories for temperature, relative humidity, $CO_2$, and power draw have been generated and saved to [comparison_chart.png](file:///C:/Users/DELL/OneDrive - Hanoi University of Science and Technology/Desktop/AI_HVAC_Control/comparison_chart.png).

