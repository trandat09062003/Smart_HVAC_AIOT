"""Lưu / đọc tiến độ train để resume sau khi tắt máy hoặc mất mạng."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def progress_path(checkpoint_dir: str) -> str:
    return os.path.join(checkpoint_dir, "train_progress.json")


def load_progress(checkpoint_dir: str) -> dict[str, Any] | None:
    path = progress_path(checkpoint_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def save_progress(
    checkpoint_dir: str,
    *,
    last_episode: int,
    rewards: list[float],
    target_episodes: int,
    extra: dict[str, Any] | None = None,
) -> None:
    os.makedirs(checkpoint_dir, exist_ok=True)
    payload: dict[str, Any] = {
        "last_episode": int(last_episode),
        "target_episodes": int(target_episodes),
        "rewards": [float(x) for x in rewards],
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if extra:
        payload.update(extra)
    path = progress_path(checkpoint_dir)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)
