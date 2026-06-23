# data/weather_gen.py
"""Sinh dữ liệu thời tiết mô phỏng (Section 3.3.5) — profile Hà Nội mùa nóng ẩm."""
import numpy as np


class WeatherGenerator:
    """
    Thời tiết mô phỏng tháng 5–10, bước 15 phút (96 bước/ngày).
    Cùng cấu trúc bài báo Guo et al. 2025; tham số nhiệt độ/ẩm theo khí hậu Hà Nội.
    """

    T_MEAN = {5: 28.0, 6: 30.5, 7: 31.0, 8: 30.5, 9: 29.0, 10: 26.5}
    T_STD = 2.5

    def __init__(self, seed: int | None = None):
        if seed is not None:
            np.random.seed(seed)

    def generate_day(self, month: int):
        """Trả về (96,) arrays: T_oa [°C], omega_oa [kg/kg], q_sol [W/m²], C_PM_oa [µg/m³]."""
        if month not in self.T_MEAN:
            month = 7
        T_base = self.T_MEAN[month] + self.T_STD * np.random.randn()
        hours = np.linspace(0, 24, 96, endpoint=False)

        T_oa = T_base + 4.0 * np.sin(2 * np.pi * (hours - 9) / 24)
        T_oa += np.random.normal(0, 0.6, 96)
        T_oa = np.clip(T_oa, 22, 42)

        omega_oa = 0.016 + 0.0015 * (T_oa - 28) / 5
        omega_oa += np.random.normal(0, 0.0012, 96)
        omega_oa = np.clip(omega_oa, 0.008, 0.024)

        q_sol = np.maximum(
            0.0,
            750.0 * np.sin(np.pi * (hours - 6) / 12) * ((hours >= 6) & (hours <= 18)).astype(float),
        )
        q_sol += np.random.normal(0, 30, 96)
        q_sol = np.clip(q_sol, 0, 900)

        pm25_base = np.clip(np.random.lognormal(2.9, 0.7), 5, 80)
        C_PM_oa = np.ones(96) * pm25_base
        C_PM_oa += np.random.normal(0, 2.0, 96)
        C_PM_oa = np.clip(C_PM_oa, 0, 80)

        return T_oa, omega_oa, q_sol, C_PM_oa
