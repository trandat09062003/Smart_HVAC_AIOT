/**
 * LCD_Test.ino
 * 
 * Chương trình kiểm tra hoạt động của màn hình LCD I2C (1602 hoặc 2004) với ESP32-S3.
 * Kết nối chân I2C tùy biến (chung bus với cảm biến SCD30):
 *   - SDA -> GPIO8
 *   - SCL -> GPIO9
 *   - VCC -> 5V (hoặc 3.3V tùy màn hình, khuyên dùng 5V để màn sáng rõ)
 *   - GND -> GND
 * 
 * Lưu ý:
 *   - Cần cài đặt thư viện "LiquidCrystal_I2C" trong Arduino Library Manager.
 *   - Địa chỉ I2C mặc định của các module LCD thường là 0x27 hoặc 0x3F.
 */

#include <Wire.h>
#include "LiquidCrystal_I2C.h"

// Định nghĩa chân I2C cho ESP32-S3-N16R8
#define I2C_SDA 8
#define I2C_SCL 9

// Khởi tạo LCD với địa chỉ I2C 0x27, kích thước 16 cột x 2 dòng
// Nếu không chạy, hãy thử đổi địa chỉ sang 0x3F
LiquidCrystal_I2C lcd(0x27, 16, 2); 

void setup() {
  // Khởi tạo Serial Monitor để kiểm tra lỗi
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n=============================================");
  Serial.println("     KHOI TONG KIEM TRA MAN HINH LCD I2C");
  Serial.println("=============================================");
  Serial.printf("Khoi tao I2C: SDA = GPIO%d, SCL = GPIO%d...\n", I2C_SDA, I2C_SCL);

  // Khởi tạo I2C bus
  Wire.begin(I2C_SDA, I2C_SCL);
  
  // Quét địa chỉ I2C để phát hiện LCD
  Serial.println("Dang quet thiet bi tren bus I2C...");
  byte error, address;
  int nDevices = 0;
  for(address = 1; address < 127; address++ ) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.printf("  --> Phat hien thiet bi tai dia chi I2C: 0x%02X\n", address);
      nDevices++;
    }
  }
  if (nDevices == 0) {
    Serial.println("  --> CANH BAO: Khong tim thay thiet bi I2C nao. Vui long kiem tra day SDA, SCL!");
  }
  
  // Khởi tạo màn hình LCD
  Serial.println("Dang khoi tao LCD...");
  lcd.init();
  lcd.backlight(); // Bật đèn nền
  
  // In thông báo ban đầu
  lcd.setCursor(0, 0); // Cột 0, Dòng 0
  lcd.print("HVAC LCD TEST");
  
  lcd.setCursor(0, 1); // Cột 0, Dòng 1
  lcd.print("SDA:8 SCL:9 OK!");
  
  Serial.println("Khoi tao LCD hoan tat. Man hinh LCD se hien thi chu va nhap nhay den nen.");
  Serial.println("=============================================\n");
}

void loop() {
  // Hiệu ứng nhấp nháy đèn nền để kiểm tra hoạt động
  lcd.backlight();
  delay(1000);
  lcd.noBacklight();
  delay(1000);
}
