# Smart HVAC AIoT

Hệ thống giám sát và điều khiển HVAC cho phòng làm việc, kết hợp node IoT ESP32-S3, server Docker và bộ điều khiển DRL (DDPG) theo hướng tiếp cận của Guo et al., *Applied Energy*, 2025 ([DOI: 10.1016/j.apenergy.2024.124467](https://doi.org/10.1016/j.apenergy.2024.124467)).

Phần cứng đo nhiệt độ, độ ẩm, CO₂ và PM₂.₅, đẩy dữ liệu lên server qua MQTT. Server chạy inference từ model đã huấn luyện, tính setpoint (nhiệt độ mục tiêu, quạt, van thông gió, ngưỡng CO₂/RH) rồi gửi ngược về ESP32. Dashboard React hiển thị telemetry và cho phép điều khiển thủ công khi cần.

Repository: [github.com/trandat09062003/Smart_HVAC_AIOT](https://github.com/trandat09062003/Smart_HVAC_AIOT)

---

## 1. Tổng quan hệ thống

Hệ thống chia làm ba tầng:

**Tầng edge (ESP32-S3)** đọc cảm biến SCD30 (I²C) và PMS5003 (UART), điều khiển relay quạt, servo van và LED trạng thái. Firmware vẫn có logic rule cục bộ để an toàn khi mất WiFi hoặc MQTT.

**Tầng server (Docker)** gồm Mosquitto, TimescaleDB và service Python `mqtt-subscriber`. Service này lưu telemetry, expose REST API cho dashboard, và chạy **AI Zone Manager** — module inference DDPG + chính sách theo khung giờ.

**Tầng giao diện (React/Vite)** truy vấn API, vẽ biểu đồ realtime và gửi lệnh override.

Luồng dữ liệu:

```
ESP32  --[sensor/indoor]-->  Mosquitto  -->  mqtt-subscriber  -->  TimescaleDB
                                    ^                |
                                    |                v
ESP32  <--[remote-control/indoor-01]--  AI Zone Manager (DDPG / rule fallback)
```

Khi không load được trọng số model, subscriber tự chuyển sang rule-based (giờ làm việc, đêm ECO, chờ tiết kiệm, free cooling).

---

## 2. Phần cứng

| Linh kiện | Giao tiếp | GPIO |
|-----------|-----------|------|
| ESP32-S3-N16R8 | — | — |
| Sensirion SCD30 | I²C | SDA=8, SCL=9 |
| Plantower PMS5003 | UART | RX=17, TX=16 |
| Relay quạt | Digital | 4 |
| Servo van (0–90°) | PWM LEDC | 15 |
| WS2812 RGB (tùy chọn) | — | 48 |

Sơ đồ PCB và layout chân chi tiết: `docs/hardware_design_guide.md`.

---

## 3. Cấu trúc project

```
Smart_HVAC_AIOT/
├── esp32/HVAC_Control.ino          Firmware chính
├── server/mqtt-subscriber/
│   ├── subscriber.py               MQTT + DB + AI Zone Manager
│   ├── load_model.py               Export actor .h5 → .npz
│   └── actor_weights.npz           Trọng số dùng khi chạy server
├── paper_reference/
│   ├── checkpoints_v2/
│   │   ├── actor.weights.h5        Trọng số Actor (train / eval)
│   │   └── critic.weights.h5       Trọng số Critic (chỉ cần khi train tiếp)
│   ├── drl/                        DDPG agent, networks, replay buffer
│   ├── simulator/                  Hybrid simulator (5 mô hình con)
│   ├── data/                       Sinh dữ liệu thời tiết
│   ├── train.py                    Huấn luyện
│   └── evaluate.py                 Đánh giá 1 ngày mô phỏng
├── scripts/replicate_and_compare.py  So sánh DRL / RBC / Random (7 ngày)
├── docs/                           Tài liệu PCB, biểu đồ benchmark
├── src/                            Dashboard React
├── libraries/                      SparkFun SCD30, PubSubClient
├── tests/                          Sketch test từng module phần cứng
├── mosquitto/                      Cấu hình broker
├── docker-compose.yml              Dashboard :3000, MQTT :1883
└── docker-compose.alt.yml          Dashboard :3005, MQTT :1885
```

---

## 4. Model DDPG

### 4.1 Mô tả

Model là **DDPG v2** (Actor–Critic). Agent được train trong môi trường mô phỏng lai (`paper_reference/simulator/hybrid_sim.py`) gồm mô hình vỏ nhà, độ ẩm, CO₂, PM₂.₅ và HVAC. Dữ liệu thời tiết đầu vào lấy từ `SeoulWeatherGenerator` (tháng 5–10, bước 15 phút).

Hàm reward (Eq. 15–20 bài báo) phạt tiêu thụ điện và các vi phạm: nhiệt ngoài 22–24.5 °C, RH > 60%, CO₂ ≥ 1000 ppm, PM₂.₅ ≥ 10 µg/m³ (trong giờ có người).

**State** — 10 chiều, chuẩn hóa min–max trước khi vào mạng:

`[giờ, T_ngoài, ω_ngoài, q_mặt_trời, 450, PM_ngoài, T_phòng, ω_phòng, CO₂, PM_phòng]`

**Action** — 4 chiều, đầu ra tanh rồi map về [0, 1]:

| Thành phần | Ý nghĩa vật lý (ban ngày) |
|------------|---------------------------|
| a₀ | Nhiệt độ nước lạnh 5–15 °C |
| a₁ | Độ mở van gió tươi 20–100% |
| a₂ | Tốc độ quạt 10–100% |
| a₃ | Máy lọc không khí ON/OFF |

**Actor:** `Dense(256) → Dense(256) → Dense(4, tanh)`  
**Critic:** hai nhánh state/action, concat, hai lớp 256, ra Q-value.

Phiên bản v2 (`paper_reference/drl/ddpg_agent.py`) bổ sung so với bản đầu: gradient clipping, warm-up 10.000 mẫu, critic update 2 lần/bước, clip reward vào [−20, 0]. Train 5000 episode; checkpoint lưu mỗi 5 episode.

### 4.2 Hai file trong `checkpoints_v2/`

- **`actor.weights.h5`** — mạng chọn hành động. Đây là phần được deploy lên server.
- **`critic.weights.h5`** — mạng đánh giá Q(s,a), chỉ dùng khi train hoặc fine-tune, không cần lúc chạy thực tế.

File runtime trên server: `server/mqtt-subscriber/actor_weights.npz` — trích từ Actor, forward pass thuần NumPy (không cần TensorFlow trong container).

### 4.3 Kết quả benchmark (mô phỏng 7 ngày, tháng 7)

Chạy `python scripts/replicate_and_compare.py` trên model hiện có:

| | DRL | RBC | Random |
|---|:---:|:---:|:---:|
| Năng lượng (kWh/ngày) | 17.85 | 31.77 | 38.65 |
| Reward trung bình / bước | −3.50 | −6.04 | −6.82 |
| Vi phạm CO₂ (≥1000 ppm) | 0% | 0% | 0.3% |
| Vi phạm PM₂.₅ (≥10 µg/m³) | 7.0% | 2.5% | 18.3% |
| Vi phạm nhiệt (22–24.5 °C) | 62.2% | 88.4% | 89.6% |

DRL giảm khoảng 44% điện năng so với rule-based baseline và 54% so với policy ngẫu nhiên, đồng thời giữ CO₂ ổn định. Nhiệt độ trung bình trong sim mùa hè Seoul hơi cao so với dải tiện nghi — khi áp dụng thực tế ở Hà Nội nên cân nhắc train lại hoặc fine-tune với profile thời tiết địa phương.

Biểu đồ: `docs/comparison_chart.png`

### 4.4 Backup model

Bản sao đầy đủ project + weights: [Google Drive](https://drive.google.com/drive/folders/1Z_hq9zdndvTVatvJ3bc4qA17vJzMEJJC)

---

## 5. Huấn luyện model

**Yêu cầu:** Python 3.12+, TensorFlow 2.x, NumPy, Matplotlib.

```bash
pip install tensorflow numpy matplotlib

cd paper_reference
python train.py
```

`train.py` chạy 5000 episode, mỗi episode qua 6 tháng × 30 ngày × 96 bước. Weight lưu tại `paper_reference/checkpoints_v2/`. Đường cong train: `paper_reference/logs/training_curve_v2.png` (tạo sau khi train xong).

Đánh giá nhanh một ngày:

```bash
cd paper_reference
python evaluate.py
```

Notebook tương đương cho Colab: `paper_reference/train.ipynb`.

**Sau khi train**, export sang định dạng server:

```bash
python server/mqtt-subscriber/load_model.py
```

Script load `checkpoints_v2/actor.weights.h5`, trích 6 tensor (w_z1, b_z1, w_z2, b_z2, w_action, b_action) và ghi `actor_weights.npz`.

---

## 6. Triển khai và sử dụng model

### 6.1 Inference trên server

`ZoneManager` trong `subscriber.py` nhận telemetry từ MQTT, ghép state vector 10 chiều từ giá trị cảm biến thực (ước lượng ω từ RH, q_sol từ giờ trong ngày, v.v.), chuẩn hóa, chạy forward Actor, rồi map sang lệnh MQTT:

```python
a = (clip(action, -1, 1) + 1) / 2
T_chws      = 5.0 + a[0] * 10.0
target_temp = round(22.0 + (T_chws - 5.0) / 2.0, 1)
D_oa        = 0.2 + a[1] * 0.8
f_sa        = 0.1 + a[2] * 0.9
```

Chính sách theo giờ:

| Khung giờ | Policy | Ghi chú |
|-----------|--------|---------|
| 08:00–17:00 | `working_hours` | DRL hoạt động |
| 22:00–06:00 | `night_eco` | DRL hoạt động |
| Còn lại | `eco_standby` | Tắt nguồn, rule tiết kiệm |
| Override từ dashboard | `manual` | Giữ setpoint người dùng trong thời gian cấu hình |

### 6.2 Cập nhật model

**Từ Drive:** tải `actor.weights.h5`, `critic.weights.h5` vào `paper_reference/checkpoints_v2/`, và `actor_weights.npz` vào `server/mqtt-subscriber/`.

**Sau train local:**

```bash
python server/mqtt-subscriber/load_model.py
docker compose -p ai_hvac_control -f docker-compose.alt.yml build mqtt-subscriber
docker compose -p ai_hvac_control -f docker-compose.alt.yml up -d mqtt-subscriber
```

Kiểm tra log:

```bash
docker logs ai-hvac-mqtt-subscriber --tail 20
```

Cần thấy dòng `Loaded DRL actor weights successfully!`

### 6.3 MQTT

| Topic | Chiều | Payload chính |
|-------|-------|---------------|
| `sensor/indoor` | ESP → server | `temperature`, `humidity`, `co2`, `dust`, `device_id` |
| `remote-control/indoor-01` | server → ESP | `power`, `temp`, `operation_mode`, `fan_power`, `co2_max`, `humidity_max`, `damper_ratio` |

---

## 7. Cài đặt từ đầu

### Bước 1 — Clone repo

```bash
git clone https://github.com/trandat09062003/Smart_HVAC_AIOT.git
cd Smart_HVAC_AIOT
```

Model đã có sẵn trong repo. Nếu thiếu, tải từ Drive (mục 4.4).

### Bước 2 — Chạy server

Cần Docker Desktop.

```bash
# Mặc định: dashboard http://localhost:3000, MQTT 1883
docker compose up -d --build

# Hoặc chạy song song project HVAC_Control khác (tránh trùng cổng):
docker compose -p ai_hvac_control -f docker-compose.alt.yml up -d --build
# → dashboard http://localhost:3005, MQTT 1885
```

### Bước 3 — Cấu hình firmware

Mở `esp32/HVAC_Control.ino`, sửa:

```cpp
#define WIFI_SSID        "TenMangWiFi"
#define WIFI_PASSWORD    "MatKhauWiFi"
#define MQTT_SERVER      "192.168.x.x"   // IP máy chạy Docker
#define MQTT_PORT        1885            // 1883 nếu dùng docker-compose.yml
#define MQTT_DEVICE_ID   "indoor-01"
```

Upload bằng Arduino IDE (board ESP32-S3, thư viện trong `libraries/`).

### Bước 4 — Kiểm tra

1. Dashboard mở được, có dữ liệu cảm biến.
2. `docker logs ai-hvac-mqtt-subscriber -f` — MQTT connected, model loaded.
3. ESP32 nhận lệnh `remote-control/indoor-01`, quạt/van phản ứng theo setpoint.

### Bước 5 — Phát triển frontend (tùy chọn)

```bash
npm install
npm run dev
```

Dev server Vite chạy tại `http://localhost:5173`.

---

## 8. Docker

| Compose file | Dashboard | MQTT (host) | Ghi chú |
|--------------|-----------|-------------|---------|
| `docker-compose.alt.yml` | 3005 | 1885 |  |

Container `docker-compose.alt.yml`:

- `ai-hvac-mosquitto`
- `ai-hvac-timescaledb`
- `ai-hvac-mqtt-subscriber`
- `ai_hvac_control-app-1`

DB mặc định: `iotdb` / user `admin` / pass `admin123` (đổi trước khi production).

---

## 9. Dashboard

Giao diện hiển thị nhiệt độ, độ ẩm, CO₂, PM₂.₅, góc van, trạng thái Zone Manager và cho phép chỉnh power, setpoint, mode từ xa. Ngưỡng cảnh báo trên UI: CO₂ > 800 ppm (warning), > 1000 (critical); PM₂.₅ > 12 / > 35 µg/m³.

API telemetry do subscriber phục vụ trên port 5000 (nội bộ Docker network).

---

## 10. Lỗi thường gặp

**`Failed to load DRL weights`** — thiếu `actor_weights.npz` hoặc image Docker cũ. Chạy `load_model.py`, rebuild container `mqtt-subscriber`.

**Dashboard trống** — ESP32 chưa publish, sai IP/port MQTT, hoặc firewall chặn 1883/1885.

**Chỉ thấy rule, không thấy DRL** — đang trong khung `eco_standby` (17:00–22:00), hoặc inference lỗi (xem log subscriber).

**`python train.py` not found** — phải chạy từ thư mục `paper_reference/`.

**Train hết RAM** — đóng ứng dụng nặng; hoặc dùng `train.ipynb` trên Colab.

---

## 11. Tài liệu liên quan

- Paper: Guo et al., Applied Energy 2025
- Train / sim: `paper_reference/`
- Benchmark: `scripts/replicate_and_compare.py`
- PCB: `docs/hardware_design_guide.md`

---

## License

MIT
