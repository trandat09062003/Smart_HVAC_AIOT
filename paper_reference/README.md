# Paper Reference — DRL Training

Mã huấn luyện và mô phỏng DDPG theo bài báo Applied Energy 2025.

**Hướng dẫn đầy đủ:** xem [README.md](../README.md) ở thư mục gốc.

## Lệnh nhanh

```powershell
cd paper_reference
python train.py
python evaluate.py
```

**Model sau train:** `checkpoints_v2/actor.weights.h5`, `critic.weights.h5`  
**Export cho server:** `python ..\server\mqtt-subscriber\load_model.py`
