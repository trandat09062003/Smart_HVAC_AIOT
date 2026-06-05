# HVAC Control System

This repository implements a low‑cost HVAC control solution based on an ESP32‑S3 edge node and a Docker‑based central server. The system monitors indoor air quality (CO₂, PM2.5, temperature, humidity) and automatically controls a ventilation fan, a servo‑driven ventilation valve, and an onboard RGB indicator.

## Features
- **Edge node (ESP32‑S3)** reads sensors (SCD30 for CO₂/temperature/humidity, GP2Y1010 for PM2.5) and publishes telemetry via MQTT.
- **Central server** (Docker) runs Mosquitto, TimescaleDB, and a Python subscriber that stores telemetry and provides a REST API.
- **Web dashboard** (React/Vite) visualises temperature, humidity, CO₂, PM2.5 and the current valve angle.
- **Automatic control**:
  - Fan turns on when CO₂ > 800 ppm **or** PM2.5 > 50 µg/m³.
  - Servo valve angle (0‑90°) is calculated from the highest pollution ratio.
  - RGB LED (WS2812) shows system state: Blue = Cooling, Red = Heating, Green = Idle, Orange = Standby.

## Hardware Connections
| Component | ESP32 Pin |
|-----------|----------|
| SCD30 (I²C) | SDA = GPIO8, SCL = GPIO9 |
| GP2Y1010 (LED) | GPIO5 |
| GP2Y1010 (Analog) | GPIO6 |
| Relay (fan) | GPIO4 |
| Servo (valve) | GPIO7 (LED‑C PWM) |
| WS2812 RGB LED | GPIO48 |

## Setup Instructions
1. **Flash firmware** – Open `HVAC_Control.ino` in Arduino IDE, set your Wi‑Fi credentials and MQTT broker IP, then upload to the ESP32‑S3.
2. **Run Docker stack** – From the project root run:
   ```bash
   docker compose up -d --build
   ```
   This starts Mosquitto, TimescaleDB, the subscriber, and the React UI (http://localhost:3000).
3. **Access dashboard** – Open a browser at `http://localhost:3000` to monitor indoor conditions and see the current valve angle.

## License
This project is licensed under the MIT License.
