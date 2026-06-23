"""
Cấu hình huấn luyện DDPG — Guo et al., Applied Energy 2025
DOI: 10.1016/j.apenergy.2024.124467

Khác bài báo duy nhất: OCCUPANCY_FIXED = 1 (một người cố định trong phòng).
"""
import numpy as np

# --- Paper Section 3.3.5 / Table 6 ---
TRAIN_MONTHS = [5, 6, 7, 8, 9, 10]  # May–October
DAYS_PER_MONTH = 30
STEPS_PER_DAY = 96                   # 15 phút / bước
N_EPISODES = 5000
SAVE_EVERY = 5
WARMUP_SAMPLES = 10_000

OCCUPANCY_FIXED = 1
CHECKPOINT_DIR = "checkpoints"

# State normalization (10-D) — outdoor range theo khí hậu triển khai (Hà Nội hè)
STATE_MIN = np.array([0, 18, 0.006, 0, 390, 0, 15, 0.003, 400, 0], dtype=np.float32)
STATE_MAX = np.array([24, 42, 0.026, 900, 520, 80, 35, 0.022, 2000, 50], dtype=np.float32)

# Khởi tạo phòng đầu episode (paper default)
INIT_ROOM_TEMP = 24.0
INIT_ROOM_OMEGA = 0.010
INIT_ROOM_CO2 = 600.0
INIT_ROOM_PM_FRAC = 0.5  # PM_in = PM_out * frac
