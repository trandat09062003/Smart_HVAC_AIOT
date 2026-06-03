# models/upgraded_model/hanoi_simulator.py
"""
PHASE 2: HANOI ROOM SIMULATOR (TEMP + HUMIDITY + CO2)
Reads actual climate weather from Hanoi EPW weather file.
Emulates room temperature and humidity dynamics via trained XGBoost models,
and simulates indoor CO2 via a hybrid model combining the UCI Occupancy CO2 model and building physics.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import os
import pickle

class HanoiEnv:
    def __init__(self, epw_path, xgb_temp_path, xgb_rh_path, xgb_co2_path, feature_names_path):
        self.epw_path = epw_path
        
        # Load XGBoost models
        self.xgb_temp = xgb.XGBRegressor()
        self.xgb_temp.load_model(xgb_temp_path)
        self.xgb_rh = xgb.XGBRegressor()
        self.xgb_rh.load_model(xgb_rh_path)
        self.xgb_co2 = xgb.XGBRegressor()
        self.xgb_co2.load_model(xgb_co2_path)
        
        with open(feature_names_path, 'rb') as f:
            self.feature_names = pickle.load(f)
            
        # Parse EPW Weather File
        self.weather_data = self._parse_epw(epw_path)
        self.max_steps = len(self.weather_data)
        
        # Reset state parameters
        self.reset()

    def _parse_epw(self, epw_path):
        """Parse Hanoi EPW file to extract outdoor temperature, humidity, month, hour, windspeed."""
        records = []
        with open(epw_path, 'r') as f:
            for line in f:
                if line.startswith(('LOCATION', 'DESIGN', 'TYPICAL', 'GROUND', 'HOLIDAYS', 'COMMENTS', 'DATA PERIODS')):
                    continue
                parts = line.strip().split(',')
                if len(parts) >= 16:
                    month = int(parts[1])
                    day = int(parts[2])
                    hour = int(parts[3]) - 1 # EPW is 1-24, convert to 0-23
                    o_temp = float(parts[6])  # Dry bulb temperature
                    o_rh = float(parts[8])    # Relative humidity
                    wind = float(parts[21]) if parts[21] != '' else 1.5 # Wind speed
                    records.append({
                        'month': month,
                        'day': day,
                        'hour': hour,
                        'o_temp': o_temp,
                        'o_rh': o_rh,
                        'wind': wind
                    })
        print(f"[+] Loaded {len(records)} weather records from EPW file.")
        return pd.DataFrame(records)

    def reset(self, start_step=0):
        self.current_step = start_step % self.max_steps
        
        # Trạng thái môi trường trong phòng ban đầu
        self.indoor_temp = 25.0
        self.indoor_rh = 60.0
        self.indoor_co2 = 600.0  # ppm ban đầu
        
        self.ac_status = 0
        self.fan_status = 0
        self.clast_time_t = 0
        self.wlast_time_t = 0
        self.target_temp = 0.0
        
        # Tạo vector quan sát (State)
        return self._get_obs()

    def _get_obs(self):
        row = self.weather_data.iloc[self.current_step]
        # Trạng thái: [Indoor_Temp, Indoor_RH, Indoor_CO2, Outdoor_Temp, Outdoor_RH, Hour, AC_Status, Fan_Status]
        return np.array([
            self.indoor_temp,
            self.indoor_rh,
            self.indoor_co2,
            row['o_temp'],
            row['o_rh'],
            float(row['hour']),
            float(self.ac_status),
            float(self.fan_status)
        ], dtype=np.float32)

    def step(self, action_idx):
        """
        Thực hiện hành động:
        action_idx từ 0-23:
        - 0: AC OFF, Fan OFF
        - 1-11: AC ON (Setpoint 20-30°C), Fan OFF
        - 12: AC OFF, Fan ON
        - 13-23: AC ON (Setpoint 20-30°C), Fan ON
        """
        row = self.weather_data.iloc[self.current_step]
        next_row = self.weather_data.iloc[(self.current_step + 1) % self.max_steps]
        
        # Giải mã hành động
        if action_idx == 0:
            self.target_temp = 0.0
            self.ac_status = 0
            self.fan_status = 0
        elif 1 <= action_idx <= 11:
            self.target_temp = 19.0 + action_idx
            self.ac_status = 1
            self.fan_status = 0
        elif action_idx == 12:
            self.target_temp = 0.0
            self.ac_status = 0
            self.fan_status = 1
        else: # 13 to 23
            self.target_temp = action_idx + 7.0
            self.ac_status = 1
            self.fan_status = 1
            
        # Cập nhật thời gian tích lũy
        clast_time = 60 if self.ac_status == 1 else 0
        wlast_time = 60 if self.fan_status == 1 else 0
        
        self.clast_time_t = (self.clast_time_t + clast_time) if clast_time > 0 else 0
        self.wlast_time_t = (self.wlast_time_t + wlast_time) if wlast_time > 0 else 0
        
        # Tính toán chênh lệch nhiệt độ ngoài trời (Differ_Outdoor_Temp)
        differ_outdoor_temp = next_row['o_temp'] - row['o_temp']
        
        # 1. Tạo DataFrame khớp cấu trúc đặc trưng của XGBoost (Nhiệt độ & Độ ẩm)
        xgb_input = pd.DataFrame([{
            'AC_Status': self.ac_status,
            'Window_Status': self.fan_status, # Sử dụng Fan_Status thay thế cho Window_Status vật lý
            'CLast_Time': clast_time,
            'CLast_Time_T': self.clast_time_t,
            'WLast_Time': wlast_time,
            'WLast_Time_T': self.wlast_time_t,
            'Indoor_Temp': self.indoor_temp,
            'Indoor_RH': self.indoor_rh,
            'Outdoor_Temp': row['o_temp'],
            'Outdoor_RH': row['o_rh'],
            'Rain': 0.0,
            'Cloud': 10.0,
            'Windspeed': row['wind'],
            'Month': row['month'],
            'Hour': row['hour'],
            'Room_ID': 0,
            'Study_ID': 6,
            'City': 0,
            'Target_Temp': self.target_temp,
            'Differ_Outdoor_Temp': differ_outdoor_temp
        }])
        
        # Đảm bảo thứ tự cột chuẩn xác với XGBoost
        xgb_input = xgb_input[self.feature_names]
        
        # 2. Dự báo nhiệt độ & độ ẩm bằng XGBoost
        diff_temp = self.xgb_temp.predict(xgb_input)[0]
        diff_rh = self.xgb_rh.predict(xgb_input)[0]
        
        self.indoor_temp += diff_temp
        self.indoor_rh += diff_rh
        self.indoor_temp = np.clip(self.indoor_temp, 10.0, 42.0)
        self.indoor_rh = np.clip(self.indoor_rh, 10.0, 100.0)
        
        # 3. Dự báo CO2 kết hợp mô hình XGBoost thực nghiệm (UCI) và Hiệu ứng cơ học quạt thông gió
        is_office_hours = 8 <= row['hour'] < 18
        occupants = 1.0 if is_office_hours else 0.0 # 1.0 = occupied (đại diện cho có người)
        
        # Gọi mô hình XGBoost CO2 thực nghiệm từ tập UCI
        # Đặc trưng đầu vào của XGBoost CO2: ['CO2', 'Temperature', 'Humidity', 'Occupancy']
        xgb_co2_input = np.array([[self.indoor_co2, self.indoor_temp, self.indoor_rh, occupants]], dtype=np.float32)
        diff_co2 = self.xgb_co2.predict(xgb_co2_input)[0]
        
        # Cập nhật nồng độ CO2
        self.indoor_co2 += diff_co2
        
        # Nếu quạt thông gió bật, khí CO2 sạch từ ngoài (~400 ppm) tràn vào làm loãng nhanh hơn
        if self.fan_status == 1:
            co2_decay_rate = 0.55  # Giảm thêm 55% chênh lệch CO2 mỗi giờ khi bật quạt thông gió chủ động
            self.indoor_co2 = self.indoor_co2 - co2_decay_rate * (self.indoor_co2 - 400.0)
            
        self.indoor_co2 = np.clip(self.indoor_co2, 380.0, 2500.0)
        
        # 4. Tính toán phần thưởng (Reward) đa mục tiêu
        reward = self._calculate_reward(row['o_temp'])
        
        # Bước sang bước tiếp theo
        self.current_step = (self.current_step + 1) % self.max_steps
        done = False
        
        return self._get_obs(), reward, done, {}

    def _calculate_reward(self, o_temp):
        """Tính toán hàm thưởng đa mục tiêu tối ưu cả Nhiệt độ, Độ ẩm & CO2 & Điện năng"""
        # A. Nhiệt độ dễ chịu (Thermal Comfort) theo ASHRAE-55
        temp_penalty = 0.0
        if self.indoor_temp < 22.0:
            temp_penalty = -1.5 * (22.0 - self.indoor_temp) ** 2
        elif self.indoor_temp > 26.0:
            temp_penalty = -1.5 * (self.indoor_temp - 26.0) ** 2
            
        # B. Độ ẩm dễ chịu (Humidity Comfort)
        rh_penalty = 0.0
        if self.indoor_rh < 40.0:
            rh_penalty = -0.05 * (40.0 - self.indoor_rh) ** 2
        elif self.indoor_rh > 65.0:
            rh_penalty = -0.05 * (self.indoor_rh - 65.0) ** 2
            
        # C. Chất lượng không khí (CO2 Comfort)
        co2_penalty = 0.0
        if self.indoor_co2 > 800.0:
            co2_penalty = -0.005 * (self.indoor_co2 - 800.0) ** 2
            if self.indoor_co2 > 1000.0:
                co2_penalty *= 2.0
                
        # D. Tiêu thụ năng lượng (Energy Consumption)
        ac_energy_penalty = -60.0 * 0.87 if self.ac_status == 1 else 0.0
        fan_energy_penalty = -4.5 * 0.87 if self.fan_status == 1 else 0.0
        
        return temp_penalty + rh_penalty + co2_penalty + ac_energy_penalty + fan_energy_penalty
