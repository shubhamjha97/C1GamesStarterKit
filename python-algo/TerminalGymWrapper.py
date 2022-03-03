import gym
import numpy as np
from gym import spaces
import gamelib
from gamelib.util import get_command, send_command, debug_write
import json


class TerminalGymWrapper(gym.Wrapper):
    def __init__(self, config=None):
        super().__init__(None)

        # Read config and initial state
        self.config = config if config else self.load_config()
        initial_state = get_command()
        self.game_state = gamelib.GameState(self.config, initial_state)

        # Set up some constants
        self.ARENA_SIZE = self.game_state.ARENA_SIZE
        self.STATIONARY_UNIT_COUNT = 3
        self.MOBILE_UNIT_COUNT = 3
        self.NUM_UNIT_TYPES = self.STATIONARY_UNIT_COUNT + self.MOBILE_UNIT_COUNT

        self.CREATE_ACTION = 0
        self.UPGRADE_ACTION = 1
        self.DELETE_ACTION = 2

        self.WALL = config["unitInformation"][0]["shorthand"]
        self.SUPPORT = config["unitInformation"][1]["shorthand"]
        self.TURRET = config["unitInformation"][2]["shorthand"]
        self.SCOUT = config["unitInformation"][3]["shorthand"]
        self.DEMOLISHER = config["unitInformation"][4]["shorthand"]
        self.INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        self.END_TURN_ACTION = 0

        self.STATIONARY_USABLE_GRID_POINTS_COUNT = self.ARENA_SIZE * self.ARENA_SIZE / 4
        self.MOBILE_USABLE_GRID_POINTS_COUNT = self.ARENA_SIZE

        self.NUM_ACTIONS = 1 + self.USABLE_GRID_POINTS_COUNT + self.USABLE_GRID_POINTS_COUNT + self.USABLE_GRID_POINTS_COUNT * self.MOBILE_UNIT_COUNT + self.MOBILE_USABLE_GRID_POINTS_COUNT * self.MOBILE_UNIT_COUNT

        # Gym properties
        self._action_space: spaces.Discrete(n=self.NUM_ACTIONS)
        self._observation_space: spaces.Box(low=0.0, high=100.0, shape=(self.ARENA_SIZE, self.ARENA_SIZE, self.NUM_UNIT_TYPES))
        self._reward_range = (-float("inf"), float("inf"))
        self.done = False
        self.env_state = self.convert_game_state_to_env_state(self.game_state)

    def convert_game_state_to_env_state(self, game_state):
        # TODO: Add current health, current SP, MP to state
        game_map = game_state.game_map.__map
        env_state = np.zeros((self.ARENA_SIZE, self.ARENA_SIZE, self.STATIONARY_UNIT_COUNT))

        for x in range(self.ARENA_SIZE):
            for y in range(self.ARENA_SIZE):
                for unit in game_map[x,y]:
                    env_state[x][y][unit] += 1

        return env_state

    def load_config(self):
        game_state_string = get_command()
        parsed_config = None
        if "replaySave" in game_state_string:
            parsed_config = json.loads(game_state_string)
        return parsed_config

    def reset(self, **kwargs):
        self.done = False
        return self.env_state

    def step(self, action):
        if action == self.END_TURN_ACTION:
            self.game_state.submit_turn()

            game_state_string = ""
            while "turnInfo" not in game_state_string:
                game_state_string = get_command()

            state = json.loads(game_state_string)
            stateType = int(state.get("turnInfo")[0])
            if stateType == 0:
                debug_write("Got new game state. Updating Gym wrapper state.")
                self.game_state = gamelib.GameState(self.config, game_state_string)
                self.env_state = self.convert_game_state_to_env_state(self.game_state)
            elif stateType == 2:
                debug_write("Got end state, game over. Stopping algo.")
                self.done = True

        x, y, unit, action_ = self.parse_action(action)

        if action_ == 0:  # Place
            if self.game_state.attempt_spawn(unit, [x, y], num=1):  # If successfully spawned
                self.env_state[x][y][unit] += 1
        elif action_ == 1:  # Upgrade
            if self.game_state.attempt_upgrade([x, y]):  # If successfully spawned
                self.env_state[x][y][unit] += 1
        elif action_ == 2:  # Delete
            if self.game_state.attempt_remove([x, y]):  # If successfully spawned
                self.env_state[x][y][unit] = 0

        reward = self.calculate_reward(self.game_state)
        return self.env_state, reward, self.done, None

    def parse_action(self, action):
        x, y = None, None  # TODO: Calculate x, y
        unit = None
        action_ = None

        if action < 673:  # Create Stationary Unit
            action_ = self.CREATE_ACTION

            # Stationary units
            if action < 197:
                unit = self.WALL
            elif action < 393:
                unit = self.SUPPORT
            elif action < 589:
                unit = self.TURRET

            # Mobile units
            elif action < 617:
                unit = self.SCOUT
            elif action < 645:
                unit = self.DEMOLISHER
            else:
                unit = self.INTERCEPTOR

        elif action < 869:  # Upgrade unit
            action_ = self.UPGRADE_ACTION
            pass
        else: # (action < 1064), Delete unit
            action_ = self.DELETE_ACTION

        return x, y, unit, action_

    def calculate_reward(self, game_state):
        return game_state.my_health - game_state.enemy_health
