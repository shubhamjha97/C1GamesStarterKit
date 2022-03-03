import gym
import numpy as np
from gym import spaces
import gamelib

class TerminalGym(gym.Wrapper):

    # Observation space:
    # Action space: (int) 6 units x 3 actions x 196 grid coordinates + 1 (end turn)


    def __init__(self, config):
        self.num_actions = 6*3*196+1

        self.config = config

        self.WALL = config["unitInformation"][0]["shorthand"]
        self.SUPPORT = config["unitInformation"][1]["shorthand"]
        self.TURRET = config["unitInformation"][2]["shorthand"]
        self.SCOUT = config["unitInformation"][3]["shorthand"]
        self.DEMOLISHER = config["unitInformation"][4]["shorthand"]
        self.INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        self.END_TURN_ACTION = 0

        self._action_space: spaces.Discrete(n=self.num_actions, start=0)
        self._observation_space: spaces.Box() # TODO: Define
        self._reward_range: tuple[SupportsFloat, SupportsFloat] # TODO: Define

        self.env_state = np.zeros((28,28,3))
        self.game_state = gamelib.GameState(self.config, turn_state) # TODO: figure out how to give empty turn state

    def reset(self, **kwargs):
        return self.env_state

    def step(self, action):
        if action == self.END_TURN_ACTION:
            pass # TODO: end turn

        x, y, unit, action_ = parse_action(action)

        if action_ == 0: # Place
            spawn_result = self.game_state.attempt_spawn(unit, [x, y], num=1)
            if spawn_result: # If successfully spawned
                self.env_state[x][y][unit] += 1
        elif action_ == 1: # Upgrade
            upgrade_result = self.game_state.attempt_upgrade([x, y])
            if upgrade_result:  # If successfully spawned
                self.env_state[x][y][unit] += 1
        elif action_ == 2: # Delete
            remove_result = self.game_state.attempt_remove([x, y])
            if remove_result:  # If successfully spawned
                self.env_state[x][y][unit] = 0

        return self.env.step(self.action(action))
