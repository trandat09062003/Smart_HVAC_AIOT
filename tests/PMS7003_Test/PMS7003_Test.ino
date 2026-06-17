#include <Arduino.h>

// Định nghĩa chân giao tiếp UART2 cho ESP32
#define PMS_RX 16 // Nối với dây TX của cảm biến
#define PMS_TX 17 // Nối với dây RX của cảm biến

void setup() {
  // Khởi tạo Serial Monitor để in kết quả lên máy tính
  Serial.begin(115200);
  
  // Khởi tạo HardwareSerial 2 giao tiếp với PMS7003 (Baudrate mặc định: 9600)
  Serial2.begin(9600, SERIAL_8N1, PMS_RX, PMS_TX);
  
  Serial.println("Đang chờ dữ liệu từ cảm biến bụi PMS7003...");
}

void loop() {
  // PMS7003 trả về một khung dữ liệu đúng 32 bytes
  if (Serial2.available() >= 32) {
    uint8_t buffer[32];
    Serial2.readBytes(buffer, 32);

    // Kiểm tra 2 byte mốc đánh dấu đầu gói tin (Header Bytes)
    if (buffer[0] == 0x42 && buffer[1] == 0x4D) {
      Serial.println("\n[SUCCESS] Đã kết nối và đọc được luồng dữ liệu PMS7003!");

      // Trích xuất các chỉ số nồng độ bụi (Chuẩn khí quyển)
      // Dữ liệu được chia làm 2 byte (High Byte và Low Byte) nên cần dịch bit
      int pm1_0 = (buffer[10] << 8) | buffer[11];
      int pm2_5 = (buffer[12] << 8) | buffer[13];
      int pm10  = (buffer[14] << 8) | buffer[15];

      Serial.print("Nồng độ PM 1.0: "); Serial.print(pm1_0); Serial.println(" ug/m3");
      Serial.print("Nồng độ PM 2.5: "); Serial.print(pm2_5); Serial.println(" ug/m3");
      Serial.print("Nồng độ PM 10:  "); Serial.print(pm10);  Serial.println(" ug/m3");
      Serial.println("----------------------------------------");
    }
  }
}