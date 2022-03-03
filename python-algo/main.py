# TODO: rename this

from TerminalGymWrapper import TerminalGymWrapper

if __name__ == "__main__":
    env = TerminalGymWrapper(config) # TODO: Pass config
    agent = TerminalAgent() # TODO

    done = False
    while not done:
        action = env.action_space.sample()
        observation, reward, done, info = env.step(action)
