"""
DDPG training — Guo et al., Applied Energy 2025 (DOI: 10.1016/j.apenergy.2024.124467)

Theo bài báo: 5000 episode, 6 tháng (5–10) x 30 ngày x 96 bước (15 phút).
Khác bài báo: OCCUPANCY_FIXED = 1 người trong phòng (xem config.py).

Chạy từ thư mục paper_reference:
  python train.py

Biến môi trường (tùy chọn, train nhanh):
  TRAIN_EPISODES=200
  DAYS_PER_MONTH=5
"""
import os
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

N_EPISODES = int(os.getenv("TRAIN_EPISODES", str(N_EPISODES)))
DAYS_PER_MONTH = int(os.getenv("DAYS_PER_MONTH", str(DAYS_PER_MONTH)))


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


def main():
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    sim = HybridSimulator(fixed_occupancy=OCCUPANCY_FIXED)
    agent = DDPGAgentV2()
    ckpt_actor = os.path.join(CHECKPOINT_DIR, "actor.weights.h5")
    if os.path.exists(ckpt_actor):
        agent.load(CHECKPOINT_DIR)
        print(f"Resume from {CHECKPOINT_DIR}/")
    else:
        print("Training from scratch")

    weather = WeatherGenerator(seed=42)
    rewards = []

    print(
        f"DDPG | {N_EPISODES} episodes | {OCCUPANCY_FIXED} occupant(s) | "
        f"{len(TRAIN_MONTHS)} months x {DAYS_PER_MONTH} days",
        flush=True,
    )
    print(f"{'Episode':>8} | {'Avg R/step':>11} | {'Buffer':>10} | {'Status':>12}", flush=True)
    print("-" * 55, flush=True)

    for ep in range(1, N_EPISODES + 1):
        agent.noise.reset()
        avg_r = run_episode(sim, agent, weather, train=True)
        rewards.append(avg_r)

        buf = len(agent.replay_buffer)
        status = "warming up" if buf < 10_000 else "training"

        if ep == 1 or ep % SAVE_EVERY == 0:
            agent.save(CHECKPOINT_DIR)
            print(f"{ep:>8} | {avg_r:>11.4f} | {buf:>10,} | {status:>12}", flush=True)

    agent.save(CHECKPOINT_DIR)

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
    print(f"\nDone -> {CHECKPOINT_DIR}/ | {curve_path}")

    try:
        export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server", "mqtt-subscriber"))
        sys.path.insert(0, export_dir)
        os.environ["CHECKPOINT_DIR"] = os.path.abspath(CHECKPOINT_DIR)
        from load_model import export_actor_npz

        out = os.path.join(export_dir, "actor_weights.npz")
        export_actor_npz(os.environ["CHECKPOINT_DIR"], out)
        print(f"Exported -> {out}")
    except Exception as ex:
        print(f"Export skipped: {ex}")


if __name__ == "__main__":
    main()
