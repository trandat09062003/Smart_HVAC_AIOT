# Smart HVAC

Hệ thống giám sát, điều khiển tối ưu hóa thông khí và nhiệt độ điều hòa (HVAC) cho phòng làm việc sử dụng giải pháp IoT tích hợp. Hệ thống bao gồm thiết bị phần cứng (ESP32-S3), máy chủ trung tâm thu nhận dữ liệu (Python MQTT Subscriber + TimescaleDB) và giao diện giám sát trực quan (React + Vite) kết hợp mô hình giả lập Digital Twin thời tiết Hà Nội.

Dự án tối ưu hóa hiệu quả sử dụng năng lượng và chất lượng không khí thông qua **Thuật toán điều khiển theo Luật Ngưỡng (Rule-Based Control - RBC) tối ưu**, giúp tiết kiệm điện năng đáng kể so với hệ thống BMS truyền thống.

---

## Kiến trúc hệ thống

```
ESP32 (Cảm biến & Màn hình)
        │  MQTT (sensor/indoor & remote-control/#)
        ▼
Mosquitto Broker ──► mqtt-subscriber (Python) ──► TimescaleDB (Lưu trữ)
                           │
                           ├── Bộ điều khiển Luật Ngưỡng (Zone Manager)
                           └── REST API Server
                                     │
                                     ▼
                              React Dashboard
```

1. **Edge Node (ESP32-S3)**: Đọc các cảm biến môi trường (SCD30 cho CO2, Temp, Humidity và PMS7003 cho PM2.5), hiển thị lên màn hình LCD I2C và gửi dữ liệu lên MQTT Broker định kỳ mỗi 2 giây. Đồng thời, thiết bị lắng nghe tín hiệu điều khiển từ server để cập nhật trạng thái hiển thị (Setpoint, Damper, Fan).
2. **MQTT Broker (Mosquitto)**: Làm cầu nối trung gian truyền thông điệp thời gian thực giữa phần cứng và máy chủ.
3. **Backend Server (mqtt-subscriber)**: Thu nhận dữ liệu cảm biến thực tế từ MQTT, ghi nhật ký vào TimescaleDB, chạy bộ điều khiển tối ưu hóa vùng đệm hành vi (Zone Manager) và cung cấp REST API cho frontend.
4. **React Dashboard**: Giao diện người dùng thời gian thực hiển thị dữ liệu cảm biến thực tế, bảng điều khiển thiết bị giả lập, tích hợp **Digital Twin mô phỏng thời tiết Hà Nội** để so sánh trực quan lượng điện năng tiêu thụ của Luật Tối Ưu (Optimized RBC) so với BMS Mặc Định (Baseline).

---

## Thuật toán điều khiển tối ưu (Zone Manager)

Thay vì chạy điều hòa ở một chế độ cố định gây lãng phí điện năng, bộ điều khiển Zone Manager tự động điều chỉnh các thông số Setpoint nhiệt độ, van gió tươi (Damper) và tốc độ quạt dựa trên các luật ngưỡng tối ưu hóa:

1. **Chính sách lịch làm việc (Scheduled Policies)**:
   - **Giờ làm việc (Working Hours)**: Duy trì nhiệt độ mát lý tưởng ở mức 24.5°C, mở van gió tươi 50% để đảm bảo lượng oxy trong phòng, bật thông gió phụ nếu CO2 vượt ngưỡng 700 ppm.
   - **Ngủ đêm ECO (Night ECO)**: Tăng nhiệt độ lên 26.5°C, giảm tốc độ quạt xuống mức thấp nhất để hạn chế tiếng ồn, giảm mở van gió xuống 30%.
   - **Chế độ chờ (Eco Standby - Ngoài giờ)**: Khi phòng trống không có người, hệ thống tự động tắt điều hòa để đưa thiết bị về trạng thái chờ tiết kiệm năng lượng tối đa, van gió tươi chỉ giữ ở mức 20%.
2. **Chế độ làm mát tự nhiên (Free Cooling)**:
   - Hệ thống liên tục so sánh nhiệt độ trong phòng với nhiệt độ ngoài trời (outdoor temperature).
   - Nếu nhiệt độ ngoài trời mát hơn nhiệt độ phòng 1.5°C (ví dụ ban đêm hoặc lúc trời mưa), hệ thống sẽ **tắt block lạnh điều hòa**, tự động **mở van gió tươi 100%** và **chạy quạt thông gió ở mức cao nhất** (High) để hút khí mát tự nhiên từ ngoài vào phòng, giúp làm mát phòng mà không tốn điện chạy máy nén.

---

## Giao diện Dashboard (React + Vite)

Giao diện giám sát được chia làm 3 Tab chức năng chính:
- **Tổng quan**: Theo dõi dữ liệu cảm biến thực tế thời gian thực (Nhiệt độ, Độ ẩm, CO2, PM2.5) từ ESP32 gửi lên, biểu đồ lịch sử, trạng thái điều khiển tự động của Zone Manager và Panel điều khiển chỉnh tay.
- **Tòa nhà (Digital Twin)**: Trực quan hóa mô hình 3D mặt cắt tòa nhà. Chạy mô phỏng thời gian thực theo chu kỳ thời tiết Hà Nội theo các tháng mùa hè nóng ẩm (Tháng 5 - Tháng 10), hiển thị sự chênh lệch luồng khí và nhiệt độ của Zone điều khiển tối ưu vs Zone mặc định.
- **Điện năng**: Biểu đồ so sánh điện năng tiêu thụ tích lũy (kWh), công suất tức thời (W) và số tiền điện tiết kiệm được của **Luật Tối Ưu** so với **BMS Mặc Định**.

---

## Cấu trúc thư mục dự án

```
esp32/HVAC_Sensor_Node/     # Mã nguồn firmware Arduino cho ESP32-S3
server/mqtt-subscriber/     # Backend Python: subscriber nhận tin, lưu DB, API server & twin engine
src/                        # Frontend React + TypeScript styled with CSS
docs/                       # Hướng dẫn thiết kế mạch PCB phần cứng
docker-compose.yml          # Stack Docker chạy môi trường Local (:3000)
docker-compose.alt.yml      # Stack Docker chạy môi trường Server VPS (:3005)
```

---

## Hướng dẫn cài đặt và vận hành

### Yêu cầu hệ thống
- Docker và Docker Compose (được khuyên dùng để triển khai nhanh)
- Node.js (phiên bản 20 trở lên nếu phát triển frontend local)
- Arduino IDE (nếu cần chỉnh sửa và nạp code cho ESP32)

### 1. Vận hành nhanh bằng Docker Compose

#### Triển khai môi trường Local (Dashboard cổng 3000, MQTT cổng 1883):
```bash
docker compose up -d --build
```
Truy cập giao diện tại: http://localhost:3000

#### Triển khai môi trường Server/VPS (Dashboard cổng 3005, MQTT cổng 1885):
```bash
docker compose -f docker-compose.alt.yml up -d --build
```
Truy cập giao diện tại: http://localhost:3005 hoặc địa chỉ IP VPS của bạn ở cổng 3005.

### 2. Cấu hình & Nạp code cho ESP32-S3

Mở tệp `esp32/HVAC_Sensor_Node/HVAC_Sensor_Node.ino` trong Arduino IDE và điều chỉnh thông tin WiFi cũng như địa chỉ IP Server:

```cpp
#define WIFI_SSID        "Tên_WiFi_Của_Bạn"
#define WIFI_PASSWORD    "Mật_Khẩu_WiFi_Của_Bạn"
#define MQTT_SERVER      "IP_Của_Máy_Chủ"     // Địa chỉ IP máy tính chạy Docker hoặc VPS
#define MQTT_PORT        1883                 // Hoặc 1885 nếu dùng docker-compose.alt.yml
```

Các thư viện ngoại vi cần thiết đã được đính kèm sẵn trong thư mục `esp32/HVAC_Sensor_Node/src/`.

---

## Thiết kế phần cứng

| Thiết bị | Giao tiếp | Chân GPIO | Vai trò |
|----------|-----|------|---------|
| **ESP32-S3-N16R8** | — | — | Bộ vi xử lý chính |
| **Sensirion SCD30** | I²C (Wire1) | SDA=8, SCL=9 | Cảm biến đo CO2, Nhiệt độ và Độ ẩm |
| **Plantower PMS7003** | UART (Serial2) | RX=16, TX=17 | Cảm biến đo bụi mịn PM2.5 |
| **LCD 1602 I²C** | I²C (Wire) | SDA=10, SCL=11 | Màn hình hiển thị thông tin cục bộ |
| **WS2812 RGB** | Single-wire | 48 | LED hiển thị trạng thái chất lượng không khí |

Sơ đồ chân chi tiết và hướng dẫn làm mạch PCB có tại: `docs/hardware_design_guide.md`.

---

## Chi tiết các Topic MQTT

- **`sensor/indoor`** (ESP32-S3 ➡️ Server): Định dạng JSON gửi dữ liệu cảm biến thực tế.
  ```json
  {
    "device_id": "indoor-01",
    "temperature": 25.4,
    "humidity": 55.2,
    "co2": 620,
    "dust": 12.0
  }
  ```
- **`remote-control/indoor-01`** (Server ➡️ ESP32-S3): JSON truyền lệnh điều khiển tự động hoặc thủ công của hệ thống.
  ```json
  {
    "device_id": "indoor-01",
    "power": true,
    "temp": 24.5,
    "operationMode": "auto",
    "fanPower": "auto",
    "co2Max": 700.0,
    "humidityMax": 60.0
  }
  ```

---


