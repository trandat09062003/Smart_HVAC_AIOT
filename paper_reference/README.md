# Paper Reference — DRL Training

Theo **Guo et al., Applied Energy 2025** ([DOI](https://doi.org/10.1016/j.apenergy.2024.124467)).

**Khác bài báo:** `OCCUPANCY_FIXED = 1` — một người cố định trong phòng (`config.py`).

## Huấn luyện

| File | Môi trường |
|------|------------|
| `train.py` | Local CPU |
| `train.ipynb` | Colab GPU |

```bash
cd paper_reference
python train.py
```

| Tham số | Mặc định (paper) | Biến môi trường |
|---------|------------------|-----------------|
| Episodes | 5000 | `TRAIN_EPISODES` |
| Ngày/tháng | 30 | `DAYS_PER_MONTH` |
| Tháng | 5–10 | cố định trong `config.py` |
| Checkpoint | `checkpoints/` | resume tự động |

Train nhanh thử: `TRAIN_EPISODES=200 DAYS_PER_MONTH=5 python train.py`

## Export cho server

```bash
set CHECKPOINT_DIR=paper_reference/checkpoints
python server/mqtt-subscriber/load_model.py
```

## Cấu trúc

```
paper_reference/
├── config.py          Hyperparameters (paper + 1 occupant)
├── train.py           Train local
├── train.ipynb        Train Colab
├── checkpoints/       actor.weights.h5, critic.weights.h5
├── data/weather_gen.py
├── drl/               DDPG agent
└── simulator/         Hybrid sim (5 models)
```
