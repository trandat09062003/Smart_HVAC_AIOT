# models/upgraded_model/train_rl.py
"""
PHASE 3: TRAIN REINFORCEMENT LEARNING AGENT (DQN)
Trains a Deep Q-Network agent in the custom Hanoi dynamic room simulator with hybrid CO2.
Optimizes AC and ventilation fan control based on indoor Temp, Humidity, and CO2.
Saves trained weights to dqn_hvac_upgraded.weights.h5.
"""
import os
import sys
import numpy as np
import tensorflow as tf
import random
from collections import deque
import argparse
from hanoi_simulator import HanoiEnv

# Replay Buffer
class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, done = map(np.array, zip(*batch))
        return state, action, reward, next_state, done

    def __len__(self):
        return len(self.buffer)

# DQN Model
class DQN(tf.keras.Model):
    def __init__(self, num_actions):
        super(DQN, self).__init__()
        self.dense1 = tf.keras.layers.Dense(64, activation='relu')
        self.dense2 = tf.keras.layers.Dense(64, activation='relu')
        self.output_layer = tf.keras.layers.Dense(num_actions, activation='linear')

    def call(self, inputs):
        x = self.dense1(inputs)
        x = self.dense2(x)
        return self.output_layer(x)

class DQNAgent:
    def __init__(self, state_dim, num_actions, learning_rate=0.001, gamma=0.9, epsilon=1.0, epsilon_min=0.1, epsilon_decay=0.995):
        self.state_dim = state_dim
        self.num_actions = num_actions
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        
        self.model = DQN(num_actions)
        self.target_model = DQN(num_actions)
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        self.loss_fn = tf.keras.losses.MeanSquaredError()
        self.update_target_network()

    def update_target_network(self):
        self.target_model.set_weights(self.model.get_weights())

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return np.random.randint(self.num_actions)
        state = np.array([state], dtype=np.float32)
        q_values = self.model(state)
        return np.argmax(q_values[0])

    def train(self, replay_buffer, batch_size):
        if len(replay_buffer) < batch_size:
            return
        
        states, actions, rewards, next_states, dones = replay_buffer.sample(batch_size)
        
        states = tf.convert_to_tensor(states, dtype=tf.float32)
        next_states = tf.convert_to_tensor(next_states, dtype=tf.float32)
        rewards = tf.convert_to_tensor(rewards, dtype=tf.float32)
        actions = tf.convert_to_tensor(actions, dtype=tf.int32)
        dones = tf.convert_to_tensor(dones, dtype=tf.float32)

        next_q_values = self.target_model(next_states)
        max_next_q = tf.reduce_max(next_q_values, axis=1)
        target_q = rewards + (1 - dones) * self.gamma * max_next_q

        with tf.GradientTape() as tape:
            current_q_values = self.model(states)
            masks = tf.one_hot(actions, self.num_actions)
            current_q = tf.reduce_sum(current_q_values * masks, axis=1)
            loss = self.loss_fn(target_q, current_q)

        grads = tape.gradient(loss, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=int, default=100)
    parser.add_argument('--steps', type=int, default=100)  # Optimized to 100 steps for ultra-fast CPU training!
    parser.add_argument('--weather', type=str, default='../temperature_model/weather/VNM_NVN_Hanoi-Noi.Bai.Intl.AP.488200_TMYx.2009-2023.epw')
    args = parser.parse_args()

    # Resolve paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weather_path = os.path.abspath(os.path.join(base_dir, args.weather))
    xgb_temp_path = os.path.join(base_dir, "xgb_temp.json")
    xgb_rh_path = os.path.join(base_dir, "xgb_rh.json")
    xgb_co2_path = os.path.join(base_dir, "xgb_co2.json")
    feature_names_path = os.path.join(base_dir, "feature_names.pkl")

    print("[*] Loading Hanoi Climate Room Simulator for RL training...")
    env = HanoiEnv(
        epw_path=weather_path,
        xgb_temp_path=xgb_temp_path,
        xgb_rh_path=xgb_rh_path,
        xgb_co2_path=xgb_co2_path,
        feature_names_path=feature_names_path
    )

    state_dim = 8
    num_actions = 24
    agent = DQNAgent(state_dim, num_actions)
    replay_buffer = ReplayBuffer(10000)
    batch_size = 32

    print(f"[*] Training Upgraded DQN Agent: {args.episodes} episodes, {args.steps} steps per episode...")

    for ep in range(args.episodes):
        obs = env.reset(start_step=ep * args.steps)
        ep_reward = 0
        
        for step in range(args.steps):
            action_idx = agent.act(obs)
            next_obs, reward, done, info = env.step(action_idx)
            
            replay_buffer.push(obs, action_idx, reward, next_obs, done)
            
            # Train every 4 steps to optimize speed and training stability
            if step % 4 == 0:
                agent.train(replay_buffer, batch_size)
            
            obs = next_obs
            ep_reward += reward

        # Periodic target network update
        agent.update_target_network()
        
        # Print progress every 10 episodes to prevent long logs
        if (ep + 1) % 10 == 0 or ep == 0:
            print(f"  -> Episode {ep+1}/{args.episodes} Complete. Cumulative Reward: {ep_reward:.2f}, Epsilon: {agent.epsilon:.3f}")

    # Save model weights
    os.makedirs(os.path.join(base_dir, "models"), exist_ok=True)
    weights_path = os.path.join(base_dir, "models/dqn_hvac_upgraded.weights.h5")
    
    agent.model.build((None, state_dim))
    agent.model.save_weights(weights_path)
    
    print(f"\n[+] Trained DQN weights saved successfully to: {weights_path}")
    print("[*] Completed Phase 3 successfully.")

if __name__ == "__main__":
    main()
