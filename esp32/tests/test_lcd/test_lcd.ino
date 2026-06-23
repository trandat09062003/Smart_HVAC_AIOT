/**
 * test_lcd.ino — Test LCD 1602 I2C (theo schematic PCB)
 *   LCD_SDA -> GPIO10
 *   LCD_SCL -> GPIO11
 */

#include <Wire.h>
#include "src/LiquidCrystal_I2C/LiquidCrystal_I2C.h"

#define LCD_SDA 10
#define LCD_SCL 11

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Wire.begin(LCD_SDA, LCD_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("LCD Test OK!");
  lcd.setCursor(0, 1);
  lcd.print("GPIO10/11");
}

void loop() {
  lcd.backlight();
  delay(1000);
  lcd.noBacklight();
  delay(1000);
}
