"""
Chạy train.py nền — tự resume khi có mạng và process bị dừng.

Cách dùng (từ thư mục paper_reference):
  python train_daemon.py

Biến môi trường:
  TRAIN_EPISODES=5000
  DAYS_PER_MONTH=30
  PING_HOST=8.8.8.8
  DAEMON_POLL_S=30
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "train_daemon.log")
PING_HOST = os.getenv("PING_HOST", "8.8.8.8")
POLL_S = int(os.getenv("DAEMON_POLL_S", "30"))


def log(msg: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def network_ok(host: str = PING_HOST, timeout: float = 3.0) -> bool:
    try:
        socket.create_connection((host, 53), timeout=timeout)
        return True
    except OSError:
        return False


def spawn_train() -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    env.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    env.setdefault("TRAIN_EPISODES", "5000")
    env.setdefault("DAYS_PER_MONTH", "30")
    log_path = os.path.join(LOG_DIR, "train_stdout.log")
    log_f = open(log_path, "a", encoding="utf-8")
    log_f.write(f"\n--- spawn {datetime.now().isoformat()} ---\n")
    log_f.flush()
    proc = subprocess.Popen(
        [sys.executable, "-u", "train.py"],
        cwd=ROOT,
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    log(f"Started train.py (pid={proc.pid}) -> logs/train_stdout.log")
    return proc


def main() -> None:
    log("Daemon started (CPU train, auto-resume when online)")
    proc: subprocess.Popen | None = None

    try:
        while True:
            online = network_ok()
            if not online:
                if proc and proc.poll() is None:
                    log(f"Offline — train pid={proc.pid} still running locally")
                else:
                    log(f"Offline — waiting for network ({PING_HOST})...")
                time.sleep(POLL_S)
                continue

            if proc is None or proc.poll() is not None:
                code = proc.returncode if proc else None
                if proc and code == 0:
                    log("train.py finished successfully.")
                    break
                if proc:
                    log(f"train.py exited (code={code}) — restarting after network OK")
                proc = spawn_train()

            time.sleep(POLL_S)
    except KeyboardInterrupt:
        log("Daemon stopped by user")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
