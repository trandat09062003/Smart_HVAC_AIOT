# Tóm tắt cấu trúc project — Smart HVAC AIoT

Tài liệu mô tả vai trò từng thư mục và file chính trong repository.

---

## Luồng hệ thống

```
ESP32 (cảm biến) ──MQTT──► Mosquitto ──► mqtt-subscriber ──► TimescaleDB
                                ▲              │
                                │              ├── DDPG inference (actor_weights.npz)
                                │              ├── Building simulator
                                │              └── REST API
                                │                      │
ESP32 (LCD hiển thị) ◄──MQTT───┘              React Dashboard
```

---

## Thư mục gốc

| File / thư mục | Vai trò |
|----------------|---------|
| `README.md` | Hướng dẫn cài đặt, triển khai, train model |
| `docker-compose.yml` | Stack Docker local (dashboard :3000, MQTT :1883) |
| `docker-compose.alt.yml` | Stack VPS / chạy song song (dashboard :3005, MQTT :1885) |
| `Dockerfile` | Build image React dashboard (nginx) |
| `nginx.conf` | Cấu hình reverse proxy trong container app |
| `package.json` / `package-lock.json` | Dependencies frontend React + Vite |
| `vite.config.ts` / `tsconfig.json` | Cấu hình build TypeScript |
| `index.html` | Entry point Vite |
| `.env.example` | Mẫu biến môi trường (tùy chọn) |
| `.gitignore` | Loại trừ node_modules, logs, weights runtime, cache |
| `img/` | Logo dashboard (`main_logo.png`, `main_logo_2.png`) |

---

## `esp32/` — Firmware edge

| File / thư mục | Vai trò |
|----------------|---------|
| `HVAC_Sensor_Node/HVAC_Sensor_Node.ino` | **Firmware chính** — WiFi, MQTT, đọc SCD30 + PMS5003, hiển thị LCD, LED RGB |
| `HVAC_Sensor_Node/src/` | Thư viện Arduino: LiquidCrystal I2C, SparkFun SCD30, PubSubClient |
| `tests/test_lcd/` | Sketch test riêng màn hình LCD (debug phần cứng) |

**MQTT publish:** `sensor/indoor` · **Subscribe:** `remote-control/#`

---

## `server/mqtt-subscriber/` — Backend AI + API

| File | Vai trò |
|------|---------|
| `subscriber.py` | **Core server** — nhận MQTT, lưu DB, Zone Manager (DDPG + rule fallback), REST API cho dashboard |
| `building_simulator.py` | Mô phỏng tòa nhà, điện năng thiết bị, reward theo paper |
| `load_model.py` | Export `actor.weights.h5` → `actor_weights.npz` (NumPy inference) |
| `actor_weights.npz` | Trọng số deploy *(generate local, không commit)* |
| `requirements.txt` | Python deps cho container |
| `Dockerfile` | Image Python subscriber |

---

## `src/` — Dashboard React

| File / thư mục | Vai trò |
|----------------|---------|
| `App.tsx` | Layout chính, 4 tab, polling API, điều khiển từ xa |
| `types.ts` | TypeScript interfaces (telemetry, DRL panel, building sim) |
| `main.tsx` / `index.css` | Bootstrap app, global styles |
| `lib/utils.ts` | Helper `cn()` cho Tailwind |
| `components/MetricCard.tsx` | Card hiển thị metric (T, RH, CO₂, PM₂.₅) |
| `components/RealTimeChart.tsx` | Biểu đồ realtime |
| `components/ControlPanel.tsx` | Panel điều khiển thủ công HVAC |
| `components/BuildingVisualization.tsx` | Digital twin SVG tòa nhà |
| `components/DRLModelPanel.tsx` | State 10D, action 4D, reward DDPG |
| `components/DevicePowerPanel.tsx` | Cấu hình công suất thiết bị |
| `components/EnergyBreakdownChart.tsx` | Biểu đồ breakdown điện năng |

---

## `paper_reference/` — Train & mô phỏng DRL

| File / thư mục | Vai trò |
|----------------|---------|
| `train.py` | **Script train** — DDPG theo paper, 1 người cố định |
| `train.ipynb` | Notebook Colab GPU |
| `config.py` | Hyperparameters (5000 ep, tháng 5–10, …) |
| `checkpoints/` | `actor.weights.h5`, `critic.weights.h5` |
| `data/weather_gen.py` | Sinh dữ liệu thời tiết mô phỏng |
| `simulator/hybrid_sim.py` | Môi trường lai 5 mô hình (vỏ nhà, RH, CO₂, PM, HVAC) |
| `simulator/building_env.py` | Mô hình nhiệt vỏ nhà |
| `simulator/humidity_model.py` | Mô hình độ ẩm |
| `simulator/co2_model.py` | Mô hình CO₂ |
| `simulator/pm25_model.py` | Mô hình PM₂.₅ |
| `simulator/hvac_model.py` | Mô hình HVAC + điện năng |
| `drl/ddpg_agent.py` | DDPG agent v2 (train + load checkpoint) |
| `drl/networks.py` | Kiến trúc Actor-Critic |
| `drl/replay_buffer.py` | Experience replay |
| `drl/ou_noise.py` | Ornstein-Uhlenbeck exploration noise |
| `logs/` | Log train, biểu đồ *(local, không commit)* |

---

## `scripts/` — Tiện ích

| File | Vai trò |
|------|---------|
| `replicate_and_compare.py` | Benchmark DRL vs RBC vs Random 7 ngày → `docs/comparison_chart.png` |

---

## `docs/` — Tài liệu

| File | Vai trò |
|------|---------|
| `PROJECT_SUMMARY.md` | Tài liệu này — map vai trò file |
| `hardware_design_guide.md` | Sơ đồ PCB, chân GPIO |
| `comparison_chart.png` | Biểu đồ kết quả benchmark |

---

## `mosquitto/` — MQTT Broker

| File | Vai trò |
|------|---------|
| `config/mosquitto.conf` | Cấu hình broker (port, persistence) |
| `data/` | DB runtime Mosquitto *(local, không commit)* |

---

## File đã loại bỏ (không còn trong repo)

| Đã xóa | Lý do |
|--------|-------|
| `libraries/` | Trùng với `esp32/HVAC_Sensor_Node/src/` |
| `tests/` (root) | Chuyển sang `esp32/tests/` |
| `paper_reference/main.py` | Entry point cũ, không dùng |
| `paper_reference/ai_mqtt_bridge.py` | Bridge thử nghiệm, không dùng |
| `paper_reference/evaluate.py` | Script eval cũ (DDPG v1), thay bằng `scripts/replicate_and_compare.py` |
| `train_hanoi.py` / `train_hanoi.ipynb` | Đổi tên → `train.py` + `train.ipynb` |
| `checkpoints_v2/`, `checkpoints_hanoi/` | Gộp → `checkpoints/` |
| `data/hanoi_weather_gen.py` | Gộp → `data/weather_gen.py` |

---

## Quy trình làm việc thường dùng

| Mục tiêu | Lệnh / file |
|----------|-------------|
| Chạy hệ thống | `docker compose -f docker-compose.alt.yml up -d --build` |
| Train model (local) | `cd paper_reference && python train.py` |
| Train model (Colab) | Mở `paper_reference/train.ipynb` |
| Export weights | `python server/mqtt-subscriber/load_model.py` |
| Benchmark | `python scripts/replicate_and_compare.py` |
| Flash ESP32 | Upload `esp32/HVAC_Sensor_Node/HVAC_Sensor_Node.ino` |

---

## Tham chiếu

- Paper: Guo et al., *Applied Energy* 2025 — [DOI](https://doi.org/10.1016/j.apenergy.2024.124467)
- Repo: [github.com/trandat09062003/Smart_HVAC_AIOT](https://github.com/trandat09062003/Smart_HVAC_AIOT)
