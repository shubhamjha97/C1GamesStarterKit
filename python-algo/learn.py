# TODO: rename this file to algo_strategy
# TODO: Create separate files for train and play

from stable_baselines3 import PPO
from TerminalGymWrapper import TerminalGymWrapper
from stable_baselines3.common.monitor import Monitor

if __name__ == "__main__":
    env = Monitor(TerminalGymWrapper())
    agent = PPO("MultiInputPolicy", env, verbose=1)
    agent.learn(total_timesteps=100000)
