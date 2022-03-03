# TODO: rename this file to algo_strategy
from stable_baselines3 import PPO
from TerminalGymWrapper import TerminalGymWrapper

if __name__ == "__main__":
    env = TerminalGymWrapper()
    agent = PPO("MlpPolicy", env, verbose=1)
    __learn = True

    if __learn:
        agent.learn(total_timesteps=10000)
    else:
        done = False
        observation = env.reset()
        while not done:
            action = agent.predict(observation)
            observation, reward, done, info = env.step(action)