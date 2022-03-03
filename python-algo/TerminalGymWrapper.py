import gym
import numpy as np
from gym import spaces
import gamelib
from gamelib.util import get_command, send_command, debug_write
import json

class TerminalGymWrapper(gym.Wrapper):

    # Observation space:
    # Action space: (int) 6 units x 3 actions x 196 grid coordinates + 1 (end turn)


    def __init__(self, config=None):
        # TODO: call superclass __init__
        # TODO: Add current health, current SP, MP to state
        self.num_actions = 6*3*196+1 # TODO: Fix

        self.config = config if config else self.load_config()
        initial_state = get_command()
        self.game_state = gamelib.GameState(self.config, initial_state)

        self.ARENA_SIZE = self.game_state.ARENA_SIZE
        self.STATIONARY_UNIT_COUNT = 3

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

        self._action_space: spaces.Discrete(n=self.num_actions, start=0)
        self._observation_space: spaces.Box() # TODO: Define
        self._reward_range: tuple[SupportsFloat, SupportsFloat] # TODO: Define

        self.env_state = np.zeros((self.ARENA_SIZE,self.ARENA_SIZE,self.STATIONARY_UNIT_COUNT))


    def convert_game_state_to_env_state(self, game_state):
        game_map = game_state.game_map.__map
        env_state = np.zeros((self.ARENA_SIZE, self.ARENA_SIZE, self.STATIONARY_UNIT_COUNT))

        for x in range(self.ARENA_SIZE):
            for y in range(self.ARENA_SIZE):
                env_state[x][y] = # TODO:

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

            while "turnInfo" not in game_state_string:
                game_state_string = get_command()

            state = json.loads(game_state_string)
            stateType = int(state.get("turnInfo")[0])
            if stateType == 0:
                """
                This is the game turn game state message. Algo must now print to stdout 2 lines, one for build phase one for
                deploy phase. Printing is handled by the provided functions.
                """
                self.on_turn(game_state_string) # TODO: Update state
            elif stateType == 2:
                debug_write("Got end state, game over. Stopping algo.")
                self.done = True

        x, y, unit, action_ = self.parse_action(action)

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


        reward = self.calculate_reward(self.game_state)
        return self.env_state, reward, self.done, None

    def parse_action(self, action):

        x, y = None, None # TODO: Calculate x, y
        unit = None
        action_ = None

        if action < 673: # Create Stationary Unit
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

        elif action < 869: # Upgrade unit
            action_ = self.UPGRADE_ACTION
            pass
        else: # Delete unit
            action_ = self.DELETE_ACTION

        return (x, y, unit, action_)

    def calculate_reward(self, game_state):
        return self.my_health - self.enemy_health
