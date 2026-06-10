"""
Export DDPG actor weights (Keras .h5) to NumPy .npz for subscriber inference.
"""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT = os.path.join(ROOT, "paper_reference", "checkpoints_v2")
OUTPUT = os.path.join(os.path.dirname(__file__), "actor_weights.npz")

sys.path.insert(0, os.path.join(ROOT, "paper_reference"))
from drl.ddpg_agent import DDPGAgentV2  # noqa: E402


def export_actor_npz(checkpoint_dir: str = CHECKPOINT, output_path: str = OUTPUT) -> None:
    agent = DDPGAgentV2()
    agent.load(checkpoint_dir)

    layers = agent.actor.layers
    z1, z2, action = layers[1], layers[2], layers[3]
    weights = {
        "w_z1": layers[1].get_weights()[0],
        "b_z1": layers[1].get_weights()[1],
        "w_z2": layers[2].get_weights()[0],
        "b_z2": layers[2].get_weights()[1],
        "w_action": layers[3].get_weights()[0],
        "b_action": layers[3].get_weights()[1],
    }
    np.savez(output_path, **weights)
    print(f"Exported actor weights -> {output_path}")
    for key, arr in weights.items():
        print(f"  {key}: {arr.shape}")


if __name__ == "__main__":
    export_actor_npz()
