/**
 * HVAC_Sensor_Node.ino
 * 
 * HỆ THỐNG GIÁM SÁT HVAC THÔNG MINH - NODE CẢM BIẾN TÍCH HỢP LCD
 * Thiết kế cho: ESP32-S3-N16R8 + Sensirion SCD30 + Plantower PMS7003 + LCD I2C
 * Nền tảng: Arduino IDE
 * 
 * Tính năng chính:
 *   1. Đọc dữ liệu môi trường thực tế: CO2, Nhiệt độ, Độ ẩm (SCD30) và Bụi mịn PM2.5 (PMS7003).
 *   2. Hiển thị thông số trực quan lên màn hình LCD I2C (1602 hoặc 2004) dùng chung bus I2C.
 *   3. Gửi dữ liệu telemetry định kỳ lên MQTT Broker để Server AI (DRL Model) chạy mô phỏng
 *      và so sánh hiệu năng điện năng tiêu thụ với Baseline.
 *   4. Lắng nghe phản hồi từ AI Server để hiển thị trạng thái điều khiển mô phỏng (Setpoint, Damper) lên LCD.
 */

#include <Wire.h>
#include <WiFi.h>
#include "src/LiquidCrystal_I2C/LiquidCrystal_I2C.h"
#include "src/SparkFun_SCD30/SparkFun_SCD30_Arduino_Library.h" // Thư viện SCD30 cục bộ
#include "src/PubSubClient/PubSubClient.h"                   // Thư viện MQTT cục bộ

// =========================================================================
// ⚙️ CẤU HÌNH HỆ THỐNG
// =========================================================================

// 1. Cấu hình kết nối WiFi
#define WIFI_SSID        "Kata"                // Tên mạng WiFi
#define WIFI_PASSWORD    "Katana3936@"         // Mật khẩu WiFi

// 2. Cấu hình MQTT Broker (Máy tính chạy Docker)
#define MQTT_SERVER      "103.90.225.155"      // IP máy chủ Cloud VPS chạy Docker
#define MQTT_PORT        1885                  // Cổng MQTT host (docker-compose.alt.yml)
#define MQTT_DEVICE_ID   "indoor-01"           // ID thiết bị
#define MQTT_PUB_TOPIC   "sensor/indoor"       // Topic gửi dữ liệu cảm biến
#define MQTT_SUB_TOPIC   "remote-control/#"    // Topic nhận phản hồi điều khiển từ AI (để hiển thị LCD)

// 3. Cấu hình chân kết nối phần cứng (Pin Definitions)
#define I2C_SDA          8     // Chân SDA nối cảm biến SCD30 và LCD (Physical Pin 12 -> GPIO8)
#define I2C_SCL          9     // Chân SCL nối cảm biến SCD30 và LCD (Physical Pin 15 -> GPIO9)
#define PIN_RGB_WS2812   48    // Chân điều khiển LED RGB WS2812B tích hợp trên board ESP32-S3

// Cấu hình chân UART cho cảm biến bụi PMS7003
#define PMS_RX           17    // ESP32 RX <- nối TX của PMS7003
#define PMS_TX           16    // ESP32 TX -> nối RX của PMS7003 (nếu cần gửi lệnh)

// =========================================================================
// 🔄 THÔNG SỐ VÀ BIẾN TOÀN CỤC
// =========================================================================

// Khởi tạo các đối tượng
SCD30 airSensor;
bool scd30Ready = false;
LiquidCrystal_I2C lcd(0x27, 16, 2); // Khởi tạo LCD I2C 1602 (Địa chỉ 0x27)
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Biến lưu trữ dữ liệu cảm biến
float currentTemp = 25.0;
float currentHum = 50.0;
float currentCO2 = 400.0;
float currentPM25 = 0.0;

// Biến lưu trữ trạng thái mô phỏng nhận về từ AI Server
float aiSetpoint = 25.0;
float aiDamper = 0.3;
bool aiPower = true;
String aiOperationMode = "auto";
String aiFanPower = "auto";
bool receivedAiState = false;

// Quản lý thời gian
unsigned long lastReadTime = 0;
const unsigned long READ_INTERVAL = 2000;       // Đọc và gửi dữ liệu mỗi 2 giây
unsigned long lastMqttRetryTime = 0;
const unsigned long MQTT_RETRY_INTERVAL = 5000; // Thử lại MQTT sau mỗi 5 giây

// Quản lý hiển thị LCD (Chuyển đổi màn hình thông tin)
unsigned long lastLcdSwitchTime = 0;
const unsigned long LCD_SWITCH_INTERVAL = 3000; // Đổi màn hình LCD mỗi 3 giây
int lcdScreenState = 0;                         // 0: Hiện thông số thực tế, 1: Hiện mô phỏng AI

// =========================================================================
// 📺 HÀM ĐIỀU KHIỂN HIỂN THỊ LCD
// =========================================================================

void updateLCD() {
  lcd.clear();
  if (lcdScreenState == 0) {
    // --- MÀN HÌNH 1: HIỂN THỊ DỮ LIỆU CẢM BIẾN THỰC TẾ ---
    // Dòng 0: CO2:XXXX T:XX.X
    lcd.setCursor(0, 0);
    lcd.printf("CO2:%4.0f T:%4.1fC", currentCO2, currentTemp);
    
    // Dòng 1: PM25:XXX H:XX%
    lcd.setCursor(0, 1);
    lcd.printf("PM25:%3.0f H:%4.1f%%", currentPM25, currentHum);
  } else {
    // --- MÀN HÌNH 2: HIỂN THỊ TRẠNG THÁI MÔ PHỎNG AI ---
    if (!receivedAiState) {
      lcd.setCursor(0, 0);
      lcd.print("AI System Sync..");
      lcd.setCursor(0, 1);
      lcd.print("Waiting server..");
    } else {
      // Dòng 0: AI:XX.X Mode:XXX
      lcd.setCursor(0, 0);
      String modeUpper = aiOperationMode;
      modeUpper.toUpperCase();
      if (modeUpper == "AUTO") modeUpper = "AUT";
      else if (modeUpper == "COOL") modeUpper = "COL";
      else if (modeUpper == "HEAT") modeUpper = "HET";
      else if (modeUpper == "OFF") modeUpper = "OFF";
      
      lcd.printf("AI:%4.1fC AC:%-3s", aiSetpoint, modeUpper.c_str());
      
      // Dòng 1: Dmp:XX% Fan:XXX
      lcd.setCursor(0, 1);
      String fanShort = aiFanPower;
      if (fanShort.equalsIgnoreCase("medium")) fanShort = "MED";
      else if (fanShort.equalsIgnoreCase("high")) fanShort = "HI";
      else if (fanShort.equalsIgnoreCase("low")) fanShort = "LO";
      else if (fanShort.equalsIgnoreCase("auto")) fanShort = "AUT";
      
      lcd.printf("Dmp:%2.0f%% Fan:%s", aiDamper * 100.0, fanShort.c_str());
    }
  }
}

// =========================================================================
// 🌐 KẾT NỐI MẠNG (WIFI & MQTT)
// =========================================================================

void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("[WiFi] Dang ket noi toi: ");
  Serial.println(WIFI_SSID);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");
  lcd.setCursor(0, 1);
  lcd.print(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 15) {
    delay(500);
    Serial.print(".");
    lcd.setCursor(attempts % 16, 1);
    lcd.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Ket noi thanh cong!");
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected!");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP().toString());
    delay(1500);
  } else {
    Serial.println("\n[Canh bao] Khong the ket noi WiFi. Chay o che do Offline.");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connect ERR");
    lcd.setCursor(0, 1);
    lcd.print("Running Offline ");
    delay(1500);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  char message[256];
  unsigned int i = 0;
  for (i = 0; i < length && i < sizeof(message) - 1; i++) {
    message[i] = (char)payload[i];
  }
  message[i] = '\0';

  Serial.printf("\n[MQTT Sub] Nhan tin nhan tu [%s]: %s\n", topic, message);

  // Phân tích trạng thái mô phỏng AI gửi về để hiển thị lên LCD
  char* tempPtr = strstr(message, "\"temp\"");
  if (tempPtr != NULL) {
    char* valPtr = strchr(tempPtr, ':');
    if (valPtr != NULL) {
      aiSetpoint = atof(valPtr + 1);
      receivedAiState = true;
    }
  }

  char* damperPtr = strstr(message, "\"damper\"");
  if (damperPtr != NULL) {
    char* valPtr = strchr(damperPtr, ':');
    if (valPtr != NULL) {
      aiDamper = atof(valPtr + 1);
    }
  }

  char* powerPtr = strstr(message, "\"power\"");
  if (powerPtr != NULL) {
    char* valPtr = strchr(powerPtr, ':');
    if (valPtr != NULL) {
      aiPower = (strncmp(valPtr + 1, "true", 4) == 0 || strncmp(valPtr + 2, "true", 4) == 0);
    }
  }

  char* fanPowerPtr = strstr(message, "\"fanPower\"");
  if (fanPowerPtr != NULL) {
    char* valPtr = strchr(fanPowerPtr, ':');
    if (valPtr != NULL) {
      char rawFan[16];
      int idx = 0;
      char* readPtr = valPtr + 1;
      while (*readPtr == ' ' || *readPtr == '"') readPtr++;
      while (*readPtr != ',' && *readPtr != '}' && *readPtr != '"' && *readPtr != '\0' && idx < 15) {
        rawFan[idx++] = *readPtr++;
      }
      rawFan[idx] = '\0';
      aiFanPower = String(rawFan);
    }
  }

  char* opModePtr = strstr(message, "\"operationMode\"");
  if (opModePtr != NULL) {
    char* valPtr = strchr(opModePtr, ':');
    if (valPtr != NULL) {
      char rawMode[16];
      int idx = 0;
      char* readPtr = valPtr + 1;
      while (*readPtr == ' ' || *readPtr == '"') readPtr++;
      while (*readPtr != ',' && *readPtr != '}' && *readPtr != '"' && *readPtr != '\0' && idx < 15) {
        rawMode[idx++] = *readPtr++;
      }
      rawMode[idx] = '\0';
      aiOperationMode = String(rawMode);
    }
  }
}

void maintainWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    static unsigned long lastWiFiRetryTime = 0;
    unsigned long now = millis();
    if (now - lastWiFiRetryTime >= 10000) {
      lastWiFiRetryTime = now;
      Serial.println("\n[WiFi] Mat ket noi! Dang ket noi lai...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
  }
}

void maintainMQTTConnection() {
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    if (now - lastMqttRetryTime >= MQTT_RETRY_INTERVAL) {
      lastMqttRetryTime = now;
      
      if (WiFi.status() == WL_CONNECTED) {
        Serial.print("[MQTT] Dang ket noi den Broker...");
        
        if (mqttClient.connect(MQTT_DEVICE_ID)) {
          Serial.println("Thanh cong!");
          mqttClient.subscribe(MQTT_SUB_TOPIC);
          Serial.printf("[MQTT] Subscribed topic: %s\n", MQTT_SUB_TOPIC);
        } else {
          Serial.print("That bai, rc = ");
          Serial.print(mqttClient.state());
          Serial.println(". Thử lại sau 5s.");
        }
      }
    }
  } else {
    mqttClient.loop();
  }
}

// =========================================================================
// 💨 ĐỌC CẢM BIẾN BỤI MỊN PMS7003
// =========================================================================

float readPMS() {
  static uint8_t buffer[32];
  static int index = 0;
  static float pm25 = 0.0;
  
  while (Serial2.available() > 0) {
    uint8_t ch = Serial2.read();
    
    if (index == 0 && ch != 0x42) continue;
    if (index == 1 && ch != 0x4D) {
      index = 0;
      continue;
    }
    
    buffer[index++] = ch;
    
    if (index == 32) {
      index = 0;
      uint16_t sum = 0;
      for (int i = 0; i < 30; i++) {
        sum += buffer[i];
      }
      uint16_t checksum = ((uint16_t)buffer[30] << 8) | buffer[31];
      if (sum == checksum) {
        uint16_t pm25_val = ((uint16_t)buffer[12] << 8) | buffer[13];
        pm25 = (float)pm25_val;
      }
    }
  }
  return pm25;
}

// =========================================================================
// SETUP & LOOP
// =========================================================================

void setup() {
  Serial.begin(115200);
  delay(2000); // Cho cong Native USB ready

  Serial.println("\n=======================================================");
  Serial.println("  KHOI DONG NODE CAM BIEN HVAC SMART-IOT + LCD MONITOR");
  Serial.println("=======================================================");

  // Khởi tạo màn hình LCD I2C
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Smart HVAC Node ");
  lcd.setCursor(0, 1);
  lcd.print("Initializing... ");

  // Khởi tạo bus I2C tùy biến
  Serial.printf("[I2C] Khoi tao bus: SDA -> GPIO%d, SCL -> GPIO%d...\n", I2C_SDA, I2C_SCL);
  Wire.begin(I2C_SDA, I2C_SCL);

  // Khởi tạo cảm biến SCD30
  Serial.println("[SCD30] Dang ket noi voi cam bien...");
  if (airSensor.begin(Wire) == false) {
    Serial.println("[LOI] Khong tim thay cam bien SCD30!");
    scd30Ready = false;
    lcd.clear();
    lcd.print("SCD30 ConnectERR");
    delay(2000);
  } else {
    Serial.println("[SCD30] Ket noi thanh cong!");
    airSensor.setMeasurementInterval(2);
    scd30Ready = true;
  }

  // Khởi tạo cổng UART cho PMS7003
  Serial2.begin(9600, SERIAL_8N1, PMS_RX, PMS_TX);
  Serial.printf("[PMS] Khoi tao UART: RX -> GPIO%d, TX -> GPIO%d\n", PMS_RX, PMS_TX);

  // Khởi tạo mạng WiFi
  setupWiFi();

  // Cấu hình MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  Serial.println("\n>> Node cảm biến đã sẵn sàng!");
  Serial.println("-------------------------------------------------------");
}

void loop() {
  // Đọc cảm biến bụi PMS7003 liên tục
  currentPM25 = readPMS();

  // Duy trì kết nối WiFi và MQTT
  maintainWiFiConnection();
  maintainMQTTConnection();

  // Đọc dữ liệu, tính toán và gửi MQTT định kỳ mỗi 2 giây
  unsigned long now = millis();
  if (now - lastReadTime >= READ_INTERVAL) {
    lastReadTime = now;

    if (scd30Ready && airSensor.dataAvailable()) {
      currentTemp = airSensor.getTemperature();
      currentHum = airSensor.getHumidity();
      currentCO2 = airSensor.getCO2();
    }

    Serial.printf("[Sensor] CO2: %.1f ppm | Temp: %.1f *C | Hum: %.1f %% | PM2.5: %.1f ug/m3\n", 
                  currentCO2, currentTemp, currentHum, currentPM25);

    // Gửi dữ liệu cảm biến lên MQTT Broker
    if (mqttClient.connected()) {
      char jsonPayload[256];
      snprintf(jsonPayload, sizeof(jsonPayload),
               "{\"device_id\":\"%s\",\"temperature\":%.2f,\"outdoor_temperature\":%.2f,\"humidity\":%.2f,\"co2\":%d,\"dust\":%.2f}",
               MQTT_DEVICE_ID, currentTemp, (currentTemp + 3.2), currentHum, (int)currentCO2, currentPM25);

      Serial.printf("[MQTT Publish] Gui len [%s]: %s\n", MQTT_PUB_TOPIC, jsonPayload);
      mqttClient.publish(MQTT_PUB_TOPIC, jsonPayload);
    }
    
    // Cập nhật hiển thị lên LCD ngay khi có dữ liệu mới
    updateLCD();
  }

  // Cập nhật LED hệ thống mỗi 500ms (Blink/Color update)
  static unsigned long lastLedTime = 0;
  if (now - lastLedTime >= 500) {
    lastLedTime = now;
    updateSystemLED();
  }

  // Luân phiên chuyển đổi màn hình hiển thị LCD sau mỗi 3 giây
  if (now - lastLcdSwitchTime >= LCD_SWITCH_INTERVAL) {
    lastLcdSwitchTime = now;
    lcdScreenState = 1 - lcdScreenState; // Toggle giữa 0 (Sensor) và 1 (AI Simulation)
    updateLCD();
  }
}

// =========================================================================
// 💡 ĐIỀU KHIỂN LED RGB HỆ THỐNG
// =========================================================================

void updateSystemLED() {
  if (WiFi.status() != WL_CONNECTED) {
    // Nhấp nháy màu vàng cam khi mất WiFi
    static bool blink = false;
    blink = !blink;
    if (blink) neopixelWrite(PIN_RGB_WS2812, 60, 20, 0); // Vàng cam dịu
    else neopixelWrite(PIN_RGB_WS2812, 0, 0, 0);
  } else if (!mqttClient.connected()) {
    // Nhấp nháy màu đỏ khi mất MQTT
    static bool blink = false;
    blink = !blink;
    if (blink) neopixelWrite(PIN_RGB_WS2812, 80, 0, 0); // Đỏ nháy
    else neopixelWrite(PIN_RGB_WS2812, 0, 0, 0);
  } else if (!receivedAiState) {
    // Sáng màu xanh dương nhạt (cyan) khi đợi dữ liệu AI từ Server
    neopixelWrite(PIN_RGB_WS2812, 0, 40, 40);
  } else {
    // Hiển thị màu theo chế độ hoạt động của điều hòa
    if (!aiPower || aiOperationMode.equalsIgnoreCase("off")) {
      neopixelWrite(PIN_RGB_WS2812, 0, 0, 0); // Tắt hẳn LED khi điều hòa tắt
    } else if (aiOperationMode.equalsIgnoreCase("auto")) {
      neopixelWrite(PIN_RGB_WS2812, 50, 0, 70); // Tím (Auto AI điều phối)
    } else if (aiOperationMode.equalsIgnoreCase("cool")) {
      neopixelWrite(PIN_RGB_WS2812, 0, 0, 75); // Xanh dương (Làm lạnh)
    } else if (aiOperationMode.equalsIgnoreCase("heat")) {
      neopixelWrite(PIN_RGB_WS2812, 70, 15, 0); // Đỏ cam (Làm nóng)
    }
  }
}
