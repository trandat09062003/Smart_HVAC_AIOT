"""
DDPG training — Guo et al., Applied Energy 2025 (DOI: 10.1016/j.apenergy.2024.124467)

Chạy từ thư mục paper_reference:
  python train.py                    # train trực tiếp (CPU)
  python train_daemon.py             # nền + tự resume khi có mạng
  .\\start_train_background.ps1      # Windows: bật daemon ẩn

Resume: đọc checkpoints/train_progress.json + actor.weights.h5

Biến môi trường:
  TRAIN_EPISODES=5000
  DAYS_PER_MONTH=30
  CUDA_VISIBLE_DEVICES=-1            # mặc định CPU
"""
import os

# CPU only — đặt trước khi import TensorFlow
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import signal
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import (
    CHECKPOINT_DIR,
    DAYS_PER_MONTH,
    INIT_ROOM_CO2,
    INIT_ROOM_OMEGA,
    INIT_ROOM_PM_FRAC,
    INIT_ROOM_TEMP,
    N_EPISODES,
    OCCUPANCY_FIXED,
    SAVE_EVERY,
    STATE_MAX,
    STATE_MIN,
    STEPS_PER_DAY,
    TRAIN_MONTHS,
)
from data.weather_gen import WeatherGenerator
from drl.ddpg_agent import DDPGAgentV2
from simulator.hybrid_sim import HybridSimulator
from train_progress import load_progress, save_progress

N_EPISODES = int(os.getenv("TRAIN_EPISODES", str(N_EPISODES)))
DAYS_PER_MONTH = int(os.getenv("DAYS_PER_MONTH", str(DAYS_PER_MONTH)))

_AGENT: DDPGAgentV2 | None = None
_REWARDS: list[float] = []
_LAST_EP = 0
_SHUTDOWN = False


def norm(s):
    return (np.array(s, dtype=np.float32) - STATE_MIN) / (STATE_MAX - STATE_MIN + 1e-8)


def ddpg2sim(a):
    return (np.clip(a, -1, 1) + 1) / 2


def run_episode(sim, agent, weather, train=True):
    total_r, steps = 0.0, 0
    for month in TRAIN_MONTHS:
        for _ in range(DAYS_PER_MONTH):
            T_d, om_d, qs_d, pm_d = weather.generate_day(month)
            state = np.array(
                [
                    0,
                    T_d[0],
                    om_d[0],
                    qs_d[0],
                    450,
                    pm_d[0],
                    INIT_ROOM_TEMP,
                    INIT_ROOM_OMEGA,
                    INIT_ROOM_CO2,
                    pm_d[0] * INIT_ROOM_PM_FRAC,
                ],
                dtype=np.float32,
            )
            for step in range(STEPS_PER_DAY):
                state[0] = step * 0.25
                state[1] = T_d[step]
                state[2] = om_d[step]
                state[3] = qs_d[step]
                state[5] = pm_d[step]

                sn = norm(state)
                a_ddpg = agent.select_action(sn, add_noise=train)
                a_sim = ddpg2sim(a_ddpg)

                next_s, reward, _ = sim.step(state.tolist(), a_sim)
                next_s = np.array(next_s, dtype=np.float32)

                if train:
                    agent.store(sn, a_ddpg, reward, norm(next_s))
                    agent.train_step()

                state = next_s
                total_r += reward
                steps += 1

    return total_r / steps


def _handle_stop(signum, frame):
    global _SHUTDOWN
    _SHUTDOWN = True
    print(f"\n[signal {signum}] Saving checkpoint...", flush=True)


def _persist(agent: DDPGAgentV2, episode: int, rewards: list[float]) -> None:
    agent.save(CHECKPOINT_DIR)
    save_progress(
        CHECKPOINT_DIR,
        last_episode=episode,
        rewards=rewards,
        target_episodes=N_EPISODES,
    )


def main():
    global _AGENT, _REWARDS, _LAST_EP

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)

    sim = HybridSimulator(fixed_occupancy=OCCUPANCY_FIXED)
    agent = DDPGAgentV2()
    _AGENT = agent

    ckpt_actor = os.path.join(CHECKPOINT_DIR, "actor.weights.h5")
    progress = load_progress(CHECKPOINT_DIR)
    start_ep = 1
    rewards: list[float] = []

    if os.path.exists(ckpt_actor):
        agent.load(CHECKPOINT_DIR)
        print(f"Resume weights from {CHECKPOINT_DIR}/", flush=True)
    else:
        print("Training from scratch", flush=True)

    if progress:
        start_ep = int(progress.get("last_episode", 0)) + 1
        rewards = list(progress.get("rewards", []))
        print(
            f"Resume progress: episode {start_ep}/{N_EPISODES} "
            f"(saved {progress.get('updated_at', '?')})",
            flush=True,
        )

    if start_ep > N_EPISODES:
        print("Already completed all episodes.", flush=True)
        return

    _REWARDS = rewards
    weather = WeatherGenerator(seed=42)

    print(
        f"DDPG CPU | episodes {start_ep}..{N_EPISODES} | "
        f"{OCCUPANCY_FIXED} occupant | {len(TRAIN_MONTHS)} months x {DAYS_PER_MONTH} days",
        flush=True,
    )
    print(f"{'Episode':>8} | {'Avg R/step':>11} | {'Buffer':>10} | {'Status':>12}", flush=True)
    print("-" * 55, flush=True)

    for ep in range(start_ep, N_EPISODES + 1):
        if _SHUTDOWN:
            break

        agent.noise.reset()
        avg_r = run_episode(sim, agent, weather, train=True)
        rewards.append(avg_r)
        _LAST_EP = ep

        buf = len(agent.replay_buffer)
        status = "warming up" if buf < 10_000 else "training"

        if ep == start_ep or ep % SAVE_EVERY == 0 or ep == N_EPISODES:
            _persist(agent, ep, rewards)
            print(f"{ep:>8} | {avg_r:>11.4f} | {buf:>10,} | {status:>12}", flush=True)

    if _SHUTDOWN:
        _persist(agent, _LAST_EP, rewards)
        print(f"Stopped early at episode {_LAST_EP}. Resume with: python train.py", flush=True)
        return

    _persist(agent, N_EPISODES, rewards)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(rewards, color="steelblue", label=f"DDPG ({OCCUPANCY_FIXED} occupant)")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Avg Reward / step")
    ax.set_title("DDPG Training Curve (Guo et al. 2025, 1-person occupancy)")
    ax.legend()
    ax.grid(alpha=0.4)
    plt.tight_layout()
    curve_path = "logs/training_curve.png"
    plt.savefig(curve_path, dpi=150)
    print(f"\nDone -> {CHECKPOINT_DIR}/ | {curve_path}", flush=True)

    try:
        export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server", "mqtt-subscriber"))
        sys.path.insert(0, export_dir)
        os.environ["CHECKPOINT_DIR"] = os.path.abspath(CHECKPOINT_DIR)
        from load_model import export_actor_npz

        out = os.path.join(export_dir, "actor_weights.npz")
        export_actor_npz(os.environ["CHECKPOINT_DIR"], out)
        print(f"Exported -> {out}", flush=True)
    except Exception as ex:
        print(f"Export skipped: {ex}", flush=True)


if __name__ == "__main__":
    main()
