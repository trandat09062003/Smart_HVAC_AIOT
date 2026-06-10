"""
Benchmark DDPG vs RBC vs Random on the hybrid simulator.
Outputs: docs/comparison_results.md and docs/comparison_chart.png
"""
import os
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_REF = os.path.join(ROOT, "paper_reference")
DOCS = os.path.join(ROOT, "docs")
CHECKPOINT = os.path.join(PAPER_REF, "checkpoints_v2")

sys.path.insert(0, PAPER_REF)
os.chdir(PAPER_REF)

from data.weather_gen import SeoulWeatherGenerator  # noqa: E402
from drl.ddpg_agent import DDPGAgentV2  # noqa: E402
from simulator.hybrid_sim import HybridSimulator  # noqa: E402

STATE_MIN = np.array([0, -5, 0.002, 0, 390, 0, 15, 0.003, 400, 0], dtype=np.float32)
STATE_MAX = np.array([24, 40, 0.025, 900, 510, 80, 35, 0.022, 2000, 50], dtype=np.float32)


def norm(s):
    return (np.array(s) - STATE_MIN) / (STATE_MAX - STATE_MIN + 1e-8)


def ddpg2sim(a):
    return (np.clip(a, -1, 1) + 1) / 2


def run_simulation(policy_type, steps=672, seed=99):
    sim = HybridSimulator()
    weather = SeoulWeatherGenerator(seed=seed)
    agent = None

    if policy_type == "DRL":
        agent = DDPGAgentV2()
        agent.load(CHECKPOINT)

    T_oa_list, omega_oa_list, q_sol_list, pm_oa_list = [], [], [], []
    for _ in range(7):
        T_d, om_d, qs_d, pm_d = weather.generate_day(month=7)
        T_oa_list.extend(T_d)
        omega_oa_list.extend(om_d)
        q_sol_list.extend(qs_d)
        pm_oa_list.extend(pm_d)

    state = np.array(
        [0.0, T_oa_list[0], omega_oa_list[0], q_sol_list[0], 450.0, pm_oa_list[0], 24.0, 0.010, 600.0, 5.0],
        dtype=np.float32,
    )

    log = {k: [] for k in ["Tza", "phi", "CO2", "PM", "E", "r", "f_T", "f_phi", "f_co2", "f_pm", "act_Tchws", "act_Doa", "act_fsa", "act_Pair"]}

    for step in range(steps):
        hour = (step % 96) * 0.25
        state[0] = hour
        state[1:6] = [T_oa_list[step], omega_oa_list[step], q_sol_list[step], 450.0, pm_oa_list[step]]

        if policy_type == "DRL":
            a_sim = ddpg2sim(agent.select_action(norm(state), add_noise=False))
        elif policy_type == "RBC":
            a_sim = np.array([0.2, 0.125, 0.444, 1.0]) if 6.0 <= hour < 20.0 else np.array([1.0, 0.0, 0.0, 0.0])
        else:
            a_sim = (np.random.uniform(-1, 1, 4) + 1.0) / 2.0

        next_s, reward, info = sim.step(state.tolist(), a_sim)
        next_s = np.array(next_s, dtype=np.float32)

        Tza, phi, CO2, PM = next_s[6], info["phi_za"], next_s[8], next_s[9]
        f_T = max(0, Tza - 24.5) + max(0, 22.0 - Tza)
        f_ph = max(0, phi - 0.60)
        f_c = 1.0 if CO2 >= 1000.0 else 0.0
        f_pm = 1.0 if PM >= 10.0 else 0.0
        T_chws = 5.0 + a_sim[0] * 10.0
        D_oa = 0.2 + a_sim[1] * 0.8
        f_sa = 0.1 + a_sim[2] * 0.9

        for k, v in zip(
            log.keys(),
            [Tza, phi, CO2, PM, info["E_kWh"], reward, f_T, f_ph, f_c, f_pm, T_chws, D_oa, f_sa, a_sim[3]],
        ):
            log[k].append(v)

        state = next_s

    return log


def main():
    os.makedirs(DOCS, exist_ok=True)
    steps = 672

    print("[*] Simulating DRL (Trained)...")
    drl_log = run_simulation("DRL", steps=steps)
    print("[*] Simulating RBC (Baseline)...")
    rbc_log = run_simulation("RBC", steps=steps)
    print("[*] Simulating Random...")
    rnd_log = run_simulation("Random", steps=steps)

    def get_stats(log):
        days = steps / 96.0
        return {
            "avg_temp": np.mean(log["Tza"]),
            "avg_rh": np.mean(log["phi"]) * 100.0,
            "avg_co2": np.mean(log["CO2"]),
            "avg_pm": np.mean(log["PM"]),
            "daily_energy": sum(log["E"]) / days,
            "avg_reward": np.mean(log["r"]),
            "temp_violation": 100.0 * np.mean([x > 0 for x in log["f_T"]]),
            "co2_violation": 100.0 * np.mean([x > 0 for x in log["f_co2"]]),
            "pm_violation": 100.0 * np.mean([x > 0 for x in log["f_pm"]]),
        }

    drl_stats, rbc_stats, rnd_stats = get_stats(drl_log), get_stats(rbc_log), get_stats(rnd_log)
    savings_vs_rbc = (rbc_stats["daily_energy"] - drl_stats["daily_energy"]) / rbc_stats["daily_energy"] * 100.0
    savings_vs_rnd = (rnd_stats["daily_energy"] - drl_stats["daily_energy"]) / rnd_stats["daily_energy"] * 100.0

    report_path = os.path.join(DOCS, "comparison_results.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(
            f"# HVAC DRL Benchmark\n\n"
            f"| Metric | DRL | RBC | Random |\n|---|---:|---:|---:|\n"
            f"| Daily energy (kWh/day) | {drl_stats['daily_energy']:.3f} | {rbc_stats['daily_energy']:.3f} | {rnd_stats['daily_energy']:.3f} |\n"
            f"| Avg reward/step | {drl_stats['avg_reward']:.3f} | {rbc_stats['avg_reward']:.3f} | {rnd_stats['avg_reward']:.3f} |\n"
            f"| CO2 violation % | {drl_stats['co2_violation']:.1f} | {rbc_stats['co2_violation']:.1f} | {rnd_stats['co2_violation']:.1f} |\n"
            f"| Energy savings vs RBC | {savings_vs_rbc:.2f}% | — | — |\n"
        )
    print(f"[+] Report: {report_path}")

    hours = np.arange(steps) * 0.25
    plt.figure(figsize=(16, 12), dpi=150)
    for i, (key, ylabel, thr) in enumerate(
        [("Tza", "Temp (C)", None), ("CO2", "CO2 (ppm)", 1000), ("PM", "PM2.5", 10)], start=1
    ):
        plt.subplot(4, 1, i)
        plt.plot(hours[:192], drl_log[key][:192], label="DRL", color="orange", linewidth=2)
        plt.plot(hours[:192], rbc_log[key][:192], label="RBC", color="green", linestyle="--")
        if thr:
            plt.axhline(thr, color="red", linestyle=":", alpha=0.7)
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True, alpha=0.3)

    plt.subplot(4, 1, 4)
    plt.plot(hours[:192], np.array(drl_log["E"])[:192] * 4, label="DRL", color="red", linewidth=2)
    plt.plot(hours[:192], np.array(rbc_log["E"])[:192] * 4, label="RBC", color="green", linestyle="--")
    plt.ylabel("Power (kW)")
    plt.xlabel("Hour")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    chart_path = os.path.join(DOCS, "comparison_chart.png")
    plt.savefig(chart_path)
    plt.close()
    print(f"[+] Chart: {chart_path}")


if __name__ == "__main__":
    main()
