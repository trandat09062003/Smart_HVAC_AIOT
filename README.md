# Smart HVAC AIoT

Hệ thống giám sát và điều khiển HVAC thông minh cho phòng làm việc, kết hợp **ESP32-S3**, **MQTT**, **TimescaleDB** và bộ điều khiển **DDPG** theo hướng tiếp cận của Guo et al., *Applied Energy*, 2025 ([DOI: 10.1016/j.apenergy.2024.124467](https://doi.org/10.1016/j.apenergy.2024.124467)).

Node cảm biến đo nhiệt độ, độ ẩm, CO₂ và PM₂.₅, gửi telemetry lên server. Server chạy inference DRL, tính setpoint (nhiệt độ mục tiêu, quạt, van thông gió, ngưỡng CO₂/RH) và phản hồi về ESP32. Dashboard React hiển thị digital twin tòa nhà, telemetry realtime và panel điều khiển thủ công.

**Repository:** [github.com/trandat09062003/Smart_HVAC_AIOT](https://github.com/trandat09062003/Smart_HVAC_AIOT)

**Tóm tắt cấu trúc file:** [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md)

---

## Kiến trúc hệ thống

```
┌─────────────────┐     sensor/indoor      ┌──────────────┐     REST API     ┌─────────────────┐
│  ESP32-S3 Node  │ ─────────────────────► │  Mosquitto   │ ◄──────────────► │  React Dashboard │
│  SCD30 + PMS    │                        │      +       │                  │  Digital Twin    │
│  LCD I2C        │ ◄───────────────────── │ mqtt-subscr. │                  └─────────────────┘
└─────────────────┘  remote-control/...    │  + DDPG AI   │
                                           │  + Timescale │
                                           └──────────────┘
```

| Tầng | Thành phần | Vai trò |
|------|------------|---------|
| Edge | ESP32-S3 | Đọc cảm biến, hiển thị LCD, publish/subscribe MQTT |
| Server | Docker stack | Lưu telemetry, inference DDPG, mô phỏng điện năng tòa nhà |
| UI | React + Vite | Dashboard 4 tab: Tổng quan, Tòa nhà, AI/DDPG, Điện năng |

Khi không load được trọng số model, server tự chuyển sang **rule-based fallback** (giờ làm việc, đêm ECO, eco standby).

---

## Phần cứng

| Linh kiện | Giao tiếp | GPIO | Ghi chú |
|-----------|-----------|------|---------|
| ESP32-S3-N16R8 | — | — | Vi điều khiển chính |
| Sensirion SCD30 | I²C (Wire1) | SDA=8, SCL=9 | Bus riêng, địa chỉ 0x61 |
| LCD 1602/2004 | I²C (Wire) | SDA=10, SCL=11 | Bus riêng, địa chỉ 0x27 |
| Plantower PMS5003 | UART | RX=**16**, TX=**17** | PMS TX → ESP RX (GPIO16) |
| WS2812 RGB | — | 48 | LED onboard module ESP32-S3 (không trên PCB sensor) |

Chi tiết PCB: [`docs/hardware_design_guide.md`](docs/hardware_design_guide.md)

---

## Cấu trúc project

```
Smart_HVAC_AIOT/
├── esp32/
│   ├── HVAC_Sensor_Node/          Firmware chính + thư viện Arduino (src/)
│   └── tests/test_lcd/            Sketch test màn hình LCD
├── server/mqtt-subscriber/
│   ├── subscriber.py              MQTT, DB, AI Zone Manager, REST API
│   ├── building_simulator.py      Mô phỏng tòa nhà + điện năng thiết bị
│   └── load_model.py              Export actor .h5 → .npz
├── paper_reference/
│   ├── config.py                  Hyperparameters (paper + 1 occupant)
│   ├── checkpoints/               Model đã train
│   ├── train.py                   Huấn luyện DDPG (local CPU)
│   ├── train.ipynb                Huấn luyện Colab GPU
│   ├── data/weather_gen.py
│   ├── drl/                       DDPG agent
│   └── simulator/                 Hybrid simulator
├── src/                           Dashboard React (Digital Twin)
├── scripts/replicate_and_compare.py
├── docs/
├── mosquitto/
├── docker-compose.yml             Local :3000, MQTT :1883
└── docker-compose.alt.yml         VPS :3005, MQTT :1885
```

---

## Model DDPG

### State & Action

**State (10 chiều):** `[giờ, T_ngoài, ω_ngoài, q_mặt_trời, 450, PM_ngoài, T_phòng, ω_phòng, CO₂, PM_phòng]`

**Action (4 chiều, tanh → [0,1]):**

| Thành phần | Ý nghĩa |
|------------|---------|
| a₀ | Nhiệt độ nước lạnh 5–15 °C |
| a₁ | Độ mở van gió tươi 20–100% |
| a₂ | Tốc độ quạt 10–100% |
| a₃ | Máy lọc không khí ON/OFF |

**Kiến trúc:** Actor `Dense(256)→Dense(256)→Dense(4,tanh)` · Critic dual-branch 256×2

**Reward** (Eq. 15–20 bài báo): phạt điện năng + vi phạm tiện nghi (T, RH, CO₂, PM₂.₅ khi có người).

### Checkpoint

| Thư mục | Mô tả |
|---------|-------|
| `checkpoints/` | Model DDPG đã train (1 người) |
| `server/.../actor_weights.npz` | Runtime NumPy (generate, không commit) |

### Benchmark (7 ngày sim, tháng 7)

| | DRL | RBC | Random |
|---|:---:|:---:|:---:|
| Năng lượng (kWh/ngày) | 17.85 | 31.77 | 38.65 |
| Reward / bước | −3.50 | −6.04 | −6.82 |
| Vi phạm CO₂ | 0% | 0% | 0.3% |

Chạy lại: `python scripts/replicate_and_compare.py` · Biểu đồ: `docs/comparison_chart.png`

Backup weights: [Google Drive](https://drive.google.com/drive/folders/1Z_hq9zdndvTVatvJ3bc4qA17vJzMEJJC)

---

## Huấn luyện

**Yêu cầu:** Python 3.12+, TensorFlow 2.x, NumPy, Matplotlib

### Huấn luyện (theo bài báo, 1 người)

```bash
cd paper_reference
python train.py
```

Colab GPU: mở `paper_reference/train.ipynb`, bật T4, chạy all cells.

Mặc định paper: **5000 episode**, tháng **5–10**, **30 ngày/tháng**. Train nhanh: `TRAIN_EPISODES=200 DAYS_PER_MONTH=5 python train.py`

### Export cho server

```bash
set CHECKPOINT_DIR=paper_reference/checkpoints
python server/mqtt-subscriber/load_model.py
```

---

## Cài đặt nhanh

### 1. Clone & chạy server

```bash
git clone https://github.com/trandat09062003/Smart_HVAC_AIOT.git
cd Smart_HVAC_AIOT
docker compose up -d --build
# Dashboard: http://localhost:3000  |  MQTT: 1883
```

Chạy song song project khác (tránh trùng cổng):

```bash
docker compose -p smart_hvac -f docker-compose.alt.yml up -d --build
# Dashboard: http://localhost:3005  |  MQTT: 1885
```

### 2. Cấu hình firmware

Sửa `esp32/HVAC_Sensor_Node/HVAC_Sensor_Node.ino`:

```cpp
#define WIFI_SSID        "TenMangWiFi"
#define WIFI_PASSWORD    "MatKhauWiFi"
#define MQTT_SERVER      "192.168.1.100"   // IP máy/VPS chạy Docker
#define MQTT_PORT        1885              // 1883 nếu dùng docker-compose.yml
#define MQTT_DEVICE_ID   "indoor-01"
```

Upload bằng Arduino IDE (board ESP32-S3). Thư viện có sẵn trong `esp32/HVAC_Sensor_Node/src/`.

### 3. Kiểm tra

1. Dashboard hiển thị telemetry realtime (4 tab).
2. `docker logs ai-hvac-mqtt-subscriber --tail 20` → `Loaded DRL actor weights successfully!`
3. LCD ESP32 hiển thị setpoint AI và trạng thái MQTT.

### 4. Frontend dev (tùy chọn)

```bash
npm install && npm run dev
# http://localhost:5173
```

---

## MQTT Topics

| Topic | Chiều | Payload |
|-------|-------|---------|
| `sensor/indoor` | ESP → server | `temperature`, `humidity`, `co2`, `dust`, `device_id`, `sensor_ok` |
| `remote-control/indoor-01` | server → ESP | `power`, `temp`, `operation_mode`, `fan_power`, `co2_max`, `humidity_max`, `damper_ratio` |

---

## Dashboard

Giao diện gồm 4 tab:

- **Tổng quan** — metric cards, biểu đồ realtime, điều khiển từ xa
- **Tòa nhà** — digital twin SVG, trạng thái zone
- **AI/DDPG** — state vector 10D, action 4D, reward, policy
- **Điện năng** — cấu hình công suất thiết bị, breakdown điện năng mô phỏng

API REST do `mqtt-subscriber` phục vụ (port 5000 nội bộ Docker).

---

## Docker

| File | Dashboard | MQTT | Ghi chú |
|------|-----------|------|---------|
| `docker-compose.yml` | 3000 | 1883 | Triển khai đơn |
| `docker-compose.alt.yml` | 3005 | 1885 | VPS / chạy song song |

DB mặc định: `iotdb` / `admin` / `admin123` — đổi trước khi production.

---

## Xử lý sự cố

| Triệu chứng | Cách xử lý |
|-------------|------------|
| `Failed to load DRL weights` | Chạy `load_model.py`, rebuild container `mqtt-subscriber` |
| Dashboard trống / offline | Kiểm tra IP/port MQTT, firewall, firmware ESP32 |
| Chỉ thấy rule, không DRL | Xem log subscriber; kiểm tra khung giờ policy |
| Train chậm / hết RAM | Dùng `paper_reference/train.ipynb` trên Colab GPU |

---

## Tài liệu

- Paper: Guo et al., Applied Energy 2025
- Train/sim: [`paper_reference/README.md`](paper_reference/README.md)
- PCB: [`docs/hardware_design_guide.md`](docs/hardware_design_guide.md)
- Benchmark: [`scripts/replicate_and_compare.py`](scripts/replicate_and_compare.py)
- Tóm tắt file: [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md)

---

## License

MIT
