# HVAC DRL Project

---

## 📖 Overview

This repository implements a **Deep Deterministic Policy Gradient (DDPG)** controller for a central HVAC system, co‑optimising:
- Energy consumption
- Thermal comfort
- Indoor CO₂ concentration
- Indoor PM₂.5 concentration

The code follows the methodology from the paper:
> Fangzhou Guo, Sang Woo Ham, Donghun Kim, Hyeun Jun Moon. *Deep reinforcement learning control for co‑optimising energy consumption, thermal comfort, and indoor air quality in an office building.* Applied Energy, 2025. DOI: 10.1016/j.apenergy.2024.124467

---

## 📁 Repository Structure

```text
AI_HVAC_Control/
├─ esp32/                 # Arduino/PlatformIO firmware for ESP32
│   └─ HVAC_Control.ino  # Main firmware (upload with Arduino IDE)
├─ server/                # Docker‑based MQTT broker & backend services
│   └─ mqtt‑subscriber/   # Python subscriber that loads the trained model
├─ frontend/              # React dashboard (Vite + TypeScript)
├─ paper_reference/       # Research code – DRL training & evaluation
│   ├─ drl/               # Agent, networks, replay buffer, OU noise
│   ├─ simulator/         # Hybrid simulation environment
│   ├─ data/              # Input data for the simulator
│   ├─ checkpoints/       # Legacy checkpoints (optional)
│   ├─ checkpoints_v2/   # Latest trained weights (actor & critic)
│   ├─ logs/              # Training curve image, logs, etc.
│   ├─ train.py           # **Training script** (run this!)
│   ├─ evaluate.py        # Evaluation script
│   └─ README.md          # (this file)
├─ tests/                 # Unit‑/integration‑tests (optional, can be removed)
├─ libraries/             # Arduino libraries used by the ESP32 firmware
├─ Dockerfile, docker‑compose.yml
└─ README.md              # Top‑level project description (brief)
```

---

## 🚀 Quick‑Start Guide

### 1️⃣ Prerequisites

| Tool | Version |
|------|---------|
| Python | ≥3.12 (tested on 3.13) |
| TensorFlow | 2.16 |
| Node.js | ≥20 |
| Docker | ≥27 |
| Arduino IDE / PlatformIO | latest |

Install the Python requirements:

```bash
# From the repository root
pip install -r requirements.txt   # if the file exists, otherwise install manually
```

### 2️⃣ Train the DRL Agent

The **train.py** script lives under `paper_reference/`. Run it from the repository root **or** provide the full path:

```powershell
# From the repository root (recommended)
python paper_reference\train.py
```

**What happens?**
- The DDPG agent is created with the improved architecture (256‑unit hidden layers, gradient clipping, warm‑up, etc.).
- Training runs for **5 000 episodes** (see `N_EPISODES = 5000` in `train.py`).
- Every 5 episodes the model weights are saved to `paper_reference/checkpoints_v2/`.
- A training‑curve image is written to `paper_reference/logs/training_curve_v2.png`.

> ⚠️ **Common error** – `python train.py` fails because the script is not in the working directory. Always use the relative path shown above or add a small wrapper script (`run_training.bat`).

### 3️⃣ Load the Trained Model on the Server

The MQTT subscriber in `server/mqtt‑subscriber/` expects the weights in `paper_reference/checkpoints_v2/`. After training completes, start the Docker stack:

```bash
docker compose up -d   # starts Mosquitto broker, backend, and (optionally) the dashboard
```

Then launch the subscriber (inside `server/mqtt‑subscriber/`):

```bash
python load_model.py   # this script calls DDPGAgentV2().load('paper_reference/checkpoints_v2')
```

### 4️⃣ Flash the ESP32 Firmware

Open `esp32/HVAC_Control.ino` in the Arduino IDE (or VS Code with PlatformIO) and upload it to your ESP32 board. The firmware connects to the MQTT broker and receives the action set‑points from the backend.

### 5️⃣ Run the Frontend Dashboard (optional)

```bash
cd frontend
npm install
npm run dev   # Vite dev server on http://localhost:5173
```

The dashboard visualises temperature, CO₂, PM₂.5, and energy‑use metrics in real time.

---

## 🛠️ Detailed Commands Reference

| Step | Command | Description |
|------|---------|-------------|
| **Train** | `python paper_reference\train.py` | Starts training (5 000 episodes). |
| **Eval** | `python paper_reference\evaluate.py` | Runs evaluation on saved checkpoints. |
| **Server** | `docker compose up -d` | Spins up Mosquitto + backend containers. |
| **Load Model** | `python server/mqtt-subscriber/load_model.py` | Loads the latest weights into the subscriber. |
| **Flash ESP32** | (Arduino IDE) → *Upload* | Upload `esp32/HVAC_Control.ino`. |
| **Dashboard** | `npm run dev` (inside `frontend/`) | Launches the React UI. |

---

## 📂 Where to Find the Model Files

- **Actor weights:** `paper_reference/checkpoints_v2/actor.weights.h5`
- **Critic weights:** `paper_reference/checkpoints_v2/critic.weights.h5`

These files are automatically created at the end of each training run (every 5 episodes) and are loaded by the server at startup.

---

## ❓ FAQ & Troubleshooting

1. **`python train.py` not found** – you are probably in the repository root. Use the full path as shown above.
2. **Out‑of‑memory errors** – the training runs on CPU only; ensure no other heavy processes are running.
3. **Docker container cannot connect to MQTT** – verify that the MQTT broker port (`1883`) is exposed and that the ESP32 and subscriber use the same broker address (`localhost` when running locally).
4. **No `paper_reference/checkpoints_v2/` folder** – it will be created automatically on the first save. If it doesn’t appear, check the console output for permission errors.

---

## 📜 License

Add your preferred license file (e.g., MIT, Apache‑2.0) at the repository root and reference it here.

---

*This README was generated and formatted automatically to give you a smooth, end‑to‑end experience.*
