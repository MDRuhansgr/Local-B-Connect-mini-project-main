"""
Deep Reinforcement Learning Traffic Control Agent
Implements PPO-based traffic signal control with multi-objective optimization
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from collections import deque
import json
import pickle

logger = logging.getLogger(__name__)


@dataclass
class TrafficPhase:
    """Traffic signal phase definition"""
    id: int
    name: str
    green_lanes: List[int]  # Lane indices that get green
    duration_range: Tuple[int, int]  # (min, max) duration in seconds
    safety_constraints: Dict[str, Any]


@dataclass
class IntersectionState:
    """Current intersection state"""
    lane_densities: np.ndarray  # Density for each lane [0-1]
    queue_lengths: np.ndarray   # Queue length for each lane
    waiting_times: np.ndarray   # Average waiting time per lane
    phase_elapsed: float        # Time elapsed in current phase
    current_phase: int          # Current active phase
    emergency_vehicles: List[int]  # Lanes with emergency vehicles
    weather_factor: float       # Weather impact factor [0-1]
    time_of_day: float         # Normalized time [0-1]


class TrafficEnvironment(gym.Env):
    """
    Traffic Control Environment for DRL Training
    
    State Space: Lane densities, queue lengths, waiting times, phase info
    Action Space: Phase selection and duration
    Reward: Multi-objective (throughput, waiting time, fairness, emissions)
    """
    
    def __init__(
        self,
        num_lanes: int = 8,
        max_vehicles_per_lane: int = 50,
        simulation_step: float = 1.0,
        episode_length: int = 3600,  # 1 hour episodes
        reward_weights: Dict[str, float] = None
    ):
        """
        Initialize traffic environment
        
        Args:
            num_lanes: Number of intersection lanes
            max_vehicles_per_lane: Maximum vehicles per lane
            simulation_step: Simulation time step in seconds
            episode_length: Episode length in simulation steps
            reward_weights: Weights for multi-objective reward
        """
        super().__init__()
        
        self.num_lanes = num_lanes
        self.max_vehicles_per_lane = max_vehicles_per_lane
        self.simulation_step = simulation_step
        self.episode_length = episode_length
        
        # Default reward weights
        self.reward_weights = reward_weights or {
            'throughput': 0.3,
            'waiting_time': 0.4,
            'fairness': 0.2,
            'emissions': 0.1
        }
        
        # Define traffic phases (4-way intersection)
        self.phases = [
            TrafficPhase(0, "NS_Green", [0, 1, 4, 5], (5, 60), {}),      # North-South
            TrafficPhase(1, "EW_Green", [2, 3, 6, 7], (5, 60), {}),      # East-West
            TrafficPhase(2, "NS_Left", [0, 4], (5, 30), {}),             # NS Left turn
            TrafficPhase(3, "EW_Left", [2, 6], (5, 30), {}),             # EW Left turn
        ]
        
        # State space: [lane_densities, queue_lengths, waiting_times, phase_info, context]
        state_dim = (
            num_lanes +           # Lane densities
            num_lanes +           # Queue lengths  
            num_lanes +           # Waiting times
            len(self.phases) +    # Phase encoding
            4                     # Context (elapsed_time, emergency, weather, time_of_day)
        )
        
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(state_dim,), dtype=np.float32
        )
        
        # Action space: [phase_selection, duration_factor]
        self.action_space = spaces.Box(
            low=np.array([0.0, 0.0]), 
            high=np.array([1.0, 1.0]), 
            dtype=np.float32
        )
        
        # Initialize state
        self.reset()
        
        # Performance tracking
        self.episode_stats = {
            'total_throughput': 0,
            'total_waiting_time': 0,
            'phase_changes': 0,
            'emergency_responses': 0,
            'rewards': []
        }
        
        logger.info(f"Traffic environment initialized: {num_lanes} lanes, {len(self.phases)} phases")
    
    def reset(self, seed: Optional[int] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        self.current_step = 0
        self.current_phase = 0
        self.phase_start_time = 0
        self.total_vehicles_passed = 0
        
        # Initialize lane states
        self.lane_densities = np.random.uniform(0.1, 0.5, self.num_lanes)
        self.queue_lengths = np.random.randint(0, 10, self.num_lanes)
        self.waiting_times = np.random.uniform(0, 30, self.num_lanes)
        
        # Context variables
        self.emergency_vehicles = []
        self.weather_factor = np.random.uniform(0.8, 1.0)
        self.time_of_day = np.random.uniform(0, 1)
        
        # Reset episode statistics
        self.episode_stats = {
            'total_throughput': 0,
            'total_waiting_time': 0,
            'phase_changes': 0,
            'emergency_responses': 0,
            'rewards': []
        }
        
        state = self._get_state()
        info = self._get_info()
        
        return state, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one step in the environment"""
        # Decode action
        phase_selection = action[0]  # [0, 1] -> phase index
        duration_factor = action[1]  # [0, 1] -> duration multiplier
        
        # Map to discrete phase
        selected_phase = int(phase_selection * len(self.phases))
        selected_phase = min(selected_phase, len(self.phases) - 1)
        
        # Calculate phase duration
        min_dur, max_dur = self.phases[selected_phase].duration_range
        duration = min_dur + duration_factor * (max_dur - min_dur)
        
        # Execute phase change if needed
        phase_changed = False
        if selected_phase != self.current_phase:
            self._change_phase(selected_phase)
            phase_changed = True
        
        # Simulate traffic for the duration
        reward = self._simulate_traffic_step(selected_phase, duration)
        
        # Update state
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= self.episode_length
        truncated = False
        
        # Get new state and info
        state = self._get_state()
        info = self._get_info()
        info['phase_changed'] = phase_changed
        
        # Track statistics
        self.episode_stats['rewards'].append(reward)
        if phase_changed:
            self.episode_stats['phase_changes'] += 1
        
        return state, reward, done, truncated, info
    
    def _get_state(self) -> np.ndarray:
        """Get current environment state"""
        # Normalize lane densities [0, 1]
        norm_densities = np.clip(self.lane_densities, 0, 1)
        
        # Normalize queue lengths [0, 1]
        norm_queues = np.clip(self.queue_lengths / self.max_vehicles_per_lane, 0, 1)
        
        # Normalize waiting times [0, 1] (assume max 120 seconds)
        norm_waiting = np.clip(self.waiting_times / 120.0, 0, 1)
        
        # Phase encoding (one-hot)
        phase_encoding = np.zeros(len(self.phases))
        phase_encoding[self.current_phase] = 1.0
        
        # Phase elapsed time (normalized by max duration)
        max_duration = max([p.duration_range[1] for p in self.phases])
        elapsed_norm = min(self.current_step - self.phase_start_time, max_duration) / max_duration
        
        # Emergency vehicle indicator
        emergency_indicator = 1.0 if self.emergency_vehicles else 0.0
        
        # Combine all features
        state = np.concatenate([
            norm_densities,
            norm_queues, 
            norm_waiting,
            phase_encoding,
            [elapsed_norm, emergency_indicator, self.weather_factor, self.time_of_day]
        ]).astype(np.float32)
        
        return state
    
    def _simulate_traffic_step(self, phase: int, duration: float) -> float:
        """Simulate one traffic step and return reward"""
        # Get active lanes for current phase
        active_lanes = self.phases[phase].green_lanes
        
        # Traffic flow simulation
        throughput = 0
        total_waiting = 0
        
        for lane in range(self.num_lanes):
            if lane in active_lanes:
                # Green phase - vehicles can pass
                flow_rate = self._calculate_flow_rate(lane)
                vehicles_passed = flow_rate * duration * self.weather_factor
                
                # Update queue and density
                self.queue_lengths[lane] = max(0, self.queue_lengths[lane] - vehicles_passed)
                self.lane_densities[lane] *= 0.95  # Density reduces as vehicles pass
                
                throughput += vehicles_passed
                
                # Waiting time decreases for active lanes
                self.waiting_times[lane] *= 0.9
                
            else:
                # Red phase - vehicles accumulate
                arrival_rate = self._calculate_arrival_rate(lane)
                new_vehicles = arrival_rate * duration
                
                self.queue_lengths[lane] += new_vehicles
                self.lane_densities[lane] = min(1.0, self.lane_densities[lane] + new_vehicles / self.max_vehicles_per_lane)
                
                # Waiting time increases for inactive lanes
                self.waiting_times[lane] += duration
            
            total_waiting += self.waiting_times[lane] * self.queue_lengths[lane]
        
        # Update total throughput
        self.total_vehicles_passed += throughput
        self.episode_stats['total_throughput'] += throughput
        self.episode_stats['total_waiting_time'] += total_waiting
        
        # Calculate multi-objective reward
        reward = self._calculate_reward(throughput, total_waiting, phase)
        
        # Random emergency vehicle generation (low probability)
        if np.random.random() < 0.01:  # 1% chance per step
            emergency_lane = np.random.randint(0, self.num_lanes)
            if emergency_lane not in self.emergency_vehicles:
                self.emergency_vehicles.append(emergency_lane)
        
        # Clear emergency vehicles after some time
        if self.emergency_vehicles and np.random.random() < 0.3:
            self.emergency_vehicles.clear()
            self.episode_stats['emergency_responses'] += 1
        
        return reward
    
    def _calculate_flow_rate(self, lane: int) -> float:
        """Calculate vehicle flow rate for a lane"""
        base_flow = 0.5  # vehicles per second
        
        # Flow reduces with higher density
        density_factor = 1.0 - self.lane_densities[lane] * 0.5
        
        # Weather impact
        weather_factor = self.weather_factor
        
        return base_flow * density_factor * weather_factor
    
    def _calculate_arrival_rate(self, lane: int) -> float:
        """Calculate vehicle arrival rate for a lane"""
        base_arrival = 0.3  # vehicles per second
        
        # Time of day factor (rush hour simulation)
        if 0.3 <= self.time_of_day <= 0.4 or 0.7 <= self.time_of_day <= 0.8:
            time_factor = 2.0  # Rush hour
        else:
            time_factor = 1.0
        
        return base_arrival * time_factor
    
    def _calculate_reward(self, throughput: float, total_waiting: float, phase: int) -> float:
        """Calculate multi-objective reward"""
        # Throughput reward (maximize)
        throughput_reward = throughput * self.reward_weights['throughput']
        
        # Waiting time penalty (minimize)
        waiting_penalty = -total_waiting * self.reward_weights['waiting_time'] / 1000
        
        # Fairness reward (balanced lane utilization)
        lane_utilization = self.lane_densities / np.sum(self.lane_densities)
        fairness_score = 1.0 - np.std(lane_utilization)
        fairness_reward = fairness_score * self.reward_weights['fairness']
        
        # Emissions penalty (fewer stops = less emissions)
        phase_changes_penalty = -0.1 if hasattr(self, '_last_phase') and self._last_phase != phase else 0
        emissions_reward = phase_changes_penalty * self.reward_weights['emissions']
        
        # Emergency vehicle priority bonus
        emergency_bonus = 0
        if self.emergency_vehicles:
            active_lanes = self.phases[phase].green_lanes
            if any(lane in active_lanes for lane in self.emergency_vehicles):
                emergency_bonus = 5.0  # High bonus for emergency response
        
        total_reward = (
            throughput_reward + 
            waiting_penalty + 
            fairness_reward + 
            emissions_reward + 
            emergency_bonus
        )
        
        self._last_phase = phase
        return total_reward
    
    def _change_phase(self, new_phase: int):
        """Change traffic signal phase"""
        self.current_phase = new_phase
        self.phase_start_time = self.current_step
        
        # Add yellow time penalty (simplified)
        for lane in range(self.num_lanes):
            self.waiting_times[lane] += 3.0  # 3 second yellow time
    
    def _get_info(self) -> Dict:
        """Get environment info"""
        return {
            'current_phase': self.current_phase,
            'phase_name': self.phases[self.current_phase].name,
            'total_throughput': self.total_vehicles_passed,
            'avg_waiting_time': np.mean(self.waiting_times),
            'max_queue_length': np.max(self.queue_lengths),
            'emergency_vehicles': len(self.emergency_vehicles),
            'episode_step': self.current_step
        }


class PPOTrafficAgent:
    """
    PPO-based Traffic Control Agent
    
    Features:
    - Custom policy network
    - Multi-objective reward optimization  
    - Emergency vehicle priority
    - Adaptive learning rate
    - Performance monitoring
    """
    
    def __init__(
        self,
        env: TrafficEnvironment,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        device: str = "auto"
    ):
        """
        Initialize PPO agent
        
        Args:
            env: Traffic environment
            learning_rate: Learning rate for policy and value networks
            n_steps: Number of steps to run for each environment per update
            batch_size: Minibatch size
            n_epochs: Number of epochs when optimizing the surrogate loss
            gamma: Discount factor
            gae_lambda: Factor for trade-off of bias vs variance for GAE
            clip_range: Clipping parameter for PPO
            device: Device to run on
        """
        self.env = env
        
        # Initialize PPO model
        self.model = PPO(
            "MlpPolicy",
            env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=gamma,
            gae_lambda=gae_lambda,
            clip_range=clip_range,
            verbose=1,
            device=device,
            tensorboard_log="./ppo_traffic_tensorboard/"
        )
        
        # Training statistics
        self.training_stats = {
            'episodes_trained': 0,
            'total_timesteps': 0,
            'best_reward': float('-inf'),
            'avg_rewards': [],
            'training_times': []
        }
        
        logger.info("PPO Traffic Agent initialized")
    
    def train(
        self, 
        total_timesteps: int = 1000000,
        callback: Optional[BaseCallback] = None,
        save_path: str = "ppo_traffic_model"
    ):
        """
        Train the PPO agent
        
        Args:
            total_timesteps: Total timesteps to train
            callback: Training callback
            save_path: Path to save trained model
        """
        logger.info(f"Starting PPO training for {total_timesteps} timesteps")
        
        # Custom callback for monitoring
        if callback is None:
            callback = TrafficTrainingCallback()
        
        # Train the model
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            tb_log_name="PPO_Traffic"
        )
        
        # Save the trained model
        self.model.save(save_path)
        logger.info(f"Training completed. Model saved to {save_path}")
        
        # Update statistics
        self.training_stats['total_timesteps'] += total_timesteps
    
    def predict(self, observation: np.ndarray, deterministic: bool = True) -> Tuple[np.ndarray, Any]:
        """Predict action for given observation"""
        return self.model.predict(observation, deterministic=deterministic)
    
    def evaluate(
        self, 
        n_episodes: int = 100,
        render: bool = False
    ) -> Dict[str, float]:
        """
        Evaluate agent performance
        
        Args:
            n_episodes: Number of episodes to evaluate
            render: Whether to render episodes
            
        Returns:
            Evaluation metrics
        """
        logger.info(f"Evaluating agent over {n_episodes} episodes")
        
        episode_rewards = []
        episode_lengths = []
        throughputs = []
        waiting_times = []
        
        for episode in range(n_episodes):
            obs, _ = self.env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            while not done:
                action, _ = self.predict(obs, deterministic=True)
                obs, reward, done, truncated, info = self.env.step(action)
                
                episode_reward += reward
                episode_length += 1
                
                if render:
                    self.env.render()
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            throughputs.append(info.get('total_throughput', 0))
            waiting_times.append(info.get('avg_waiting_time', 0))
        
        # Calculate metrics
        metrics = {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_episode_length': np.mean(episode_lengths),
            'mean_throughput': np.mean(throughputs),
            'mean_waiting_time': np.mean(waiting_times),
            'success_rate': sum(1 for r in episode_rewards if r > 0) / len(episode_rewards)
        }
        
        logger.info(f"Evaluation results: {metrics}")
        return metrics
    
    def load_model(self, model_path: str):
        """Load pre-trained model"""
        self.model = PPO.load(model_path, env=self.env)
        logger.info(f"Model loaded from {model_path}")
    
    def get_training_stats(self) -> Dict:
        """Get training statistics"""
        return self.training_stats.copy()


class TrafficTrainingCallback(BaseCallback):
    """Custom callback for monitoring PPO training"""
    
    def __init__(self, verbose: int = 1):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        
    def _on_step(self) -> bool:
        # Log training progress
        if len(self.locals.get('infos', [])) > 0:
            info = self.locals['infos'][0]
            if 'episode' in info:
                episode_reward = info['episode']['r']
                episode_length = info['episode']['l']
                
                self.episode_rewards.append(episode_reward)
                self.episode_lengths.append(episode_length)
                
                # Log every 10 episodes
                if len(self.episode_rewards) % 10 == 0:
                    avg_reward = np.mean(self.episode_rewards[-10:])
                    avg_length = np.mean(self.episode_lengths[-10:])
                    
                    if self.verbose > 0:
                        print(f"Episode {len(self.episode_rewards)}: "
                              f"Avg Reward = {avg_reward:.2f}, "
                              f"Avg Length = {avg_length:.1f}")
        
        return True


def main():
    """Test the DRL Traffic Agent"""
    # Create environment
    env = TrafficEnvironment(
        num_lanes=8,
        episode_length=1800,  # 30 minute episodes
        reward_weights={
            'throughput': 0.3,
            'waiting_time': 0.4,
            'fairness': 0.2,
            'emissions': 0.1
        }
    )
    
    # Create agent
    agent = PPOTrafficAgent(
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64
    )
    
    # Train agent
    print("Training PPO agent...")
    agent.train(total_timesteps=100000)
    
    # Evaluate agent
    print("Evaluating trained agent...")
    metrics = agent.evaluate(n_episodes=10)
    print(f"Evaluation metrics: {metrics}")
    
    # Test real-time control
    print("Testing real-time control...")
    obs, _ = env.reset()
    
    for step in range(100):
        action, _ = agent.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)
        
        if step % 10 == 0:
            print(f"Step {step}: Phase = {info['phase_name']}, "
                  f"Reward = {reward:.2f}, "
                  f"Throughput = {info['total_throughput']:.1f}")
        
        if done:
            break


if __name__ == "__main__":
    main()