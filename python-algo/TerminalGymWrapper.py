import gym
import numpy as np
from gym import spaces
import gamelib
from gamelib.util import debug_write
import json
import time
import subprocess
import signal
import threading
from xmlrpc.client import ServerProxy

class TerminalGymWrapper(gym.Env):
    def __init__(self, config=None):

        self.turn_idx = 0
        self.current_turn_count = 0
        self.CURRENT_TURN_COUNT_THRESH = 20 # Threshold on number of actions per turn

        # Set up some constants
        self.STATIONARY_UNIT_COUNT = 3
        self.MOBILE_UNIT_COUNT = 3
        self.NUM_UNIT_TYPES = self.STATIONARY_UNIT_COUNT + self.MOBILE_UNIT_COUNT

        self.CREATE_ACTION = 0
        self.UPGRADE_ACTION = 1
        self.DELETE_ACTION = 2

        self.start_engine()

        self.WALL = self.config["unitInformation"][0]["shorthand"] # 0
        self.SUPPORT = self.config["unitInformation"][1]["shorthand"] # 1
        self.TURRET = self.config["unitInformation"][2]["shorthand"] # 2
        self.SCOUT = self.config["unitInformation"][3]["shorthand"] # 3
        self.DEMOLISHER = self.config["unitInformation"][4]["shorthand"] # 4
        self.INTERCEPTOR = self.config["unitInformation"][5]["shorthand"] # 5

        self.unit_to_int = {
            self.WALL: 0,
            "Enemy " + self.WALL: 0,
            self.SUPPORT: 1,
            "Enemy " + self.SUPPORT: 1,
            self.TURRET: 2,
            "Enemy " + self.TURRET: 2,
            self.SCOUT: 3,
            "Enemy " + self.SCOUT: 3,
            self.DEMOLISHER: 4,
            "Enemy " + self.DEMOLISHER: 4,
            self.INTERCEPTOR: 5,
            "Enemy " + self.INTERCEPTOR: 5,
        }

        self.END_TURN_ACTION = 0

        self.STATIONARY_USABLE_GRID_POINTS_COUNT = self.ARENA_SIZE * self.ARENA_SIZE / 4
        self.MOBILE_USABLE_GRID_POINTS_COUNT = self.ARENA_SIZE

        self.NUM_ACTIONS = int(1 + self.STATIONARY_USABLE_GRID_POINTS_COUNT + self.STATIONARY_USABLE_GRID_POINTS_COUNT + self.STATIONARY_USABLE_GRID_POINTS_COUNT * self.MOBILE_UNIT_COUNT + self.MOBILE_USABLE_GRID_POINTS_COUNT * self.MOBILE_UNIT_COUNT)

        self.COORD_MAP = None
        # TODO: add logic here instead of reading file
        with open('python-algo/coord_mapping.json', 'r') as f:
            self.COORD_MAP = json.load(f)
        self.COORD_MAP = {int(k):v for k,v in self.COORD_MAP.items()}

        # Gym properties
        self.action_space = spaces.Discrete(n=self.NUM_ACTIONS)
        # TODO: Convert to dict
        self.observation_space = spaces.Box(low=0.0, high=100.0, shape=(self.ARENA_SIZE, self.ARENA_SIZE, self.NUM_UNIT_TYPES))
        self.reward_range = (-float("inf"), float("inf"))
        self.done = False


    def start_engine(self):
        debug_write("Starting engine.")
        self.engine_process = subprocess.Popen(
            "cd /Users/sjha/Documents/C1GamesStarterKit; ./scripts/run_match.sh python-algo python-algo-orig",
            shell=True)
        time.sleep(3)

        # Establish RPC connection to server
        self.remote = ServerProxy('http://localhost:50000', verbose=False, allow_none=True)

        # Read config and initial state
        self.config = self.load_config()
        initial_state = self.get_command()
        self.game_state = gamelib.GameState(self.config, initial_state)
        self.ARENA_SIZE = self.game_state.ARENA_SIZE
        self.env_state = self.convert_game_state_to_env_state(self.game_state)

    def kill_rpc(self):
        self.remote.kill()

    def stop_engine(self):
        self.kill_rpc()
        time.sleep(1)
        debug_write("Sending SIGKILL.")
        self.engine_process.send_signal(signal.SIGKILL)

    def restart_engine(self):
        self.stop_engine()
        debug_write("Engine stopped.")
        time.sleep(3)
        debug_write("Restarting engine.")
        self.start_engine()
        debug_write("Engine restaeted") # TODO: remove

    def get_command(self):
        resp = self.remote.get_command()
        return resp

    def send_command(self, cmd):
        self.remote.send_command(cmd)

    def convert_game_state_to_env_state(self, game_state):
        # TODO: Add current health, current SP, MP to state
        game_map = getattr(game_state.game_map, "_GameMap__map")
        env_state = np.zeros((self.ARENA_SIZE, self.ARENA_SIZE, self.NUM_UNIT_TYPES))

        for x in range(self.ARENA_SIZE):
            for y in range(self.ARENA_SIZE):
                for unit in game_map[x][y]:
                    env_state[x][y][self.unit_to_int[unit.unit_type]] += 1 # TODO: Treat own and enemy units differently

        return env_state

    def load_config(self):
        debug_write("loading config")
        game_state_string = self.get_command()
        parsed_config = json.loads(game_state_string)
        return parsed_config

    def reset(self, **kwargs):
        self.restart_engine()
        self.done = False
        return self.env_state

    def submit_turn(self):
        build_string = json.dumps(self.game_state._build_stack)
        deploy_string = json.dumps(self.game_state._deploy_stack)
        self.send_command(build_string)
        self.send_command(deploy_string)

    def step(self, action):
        if action == self.END_TURN_ACTION or self.current_turn_count >= self.CURRENT_TURN_COUNT_THRESH:
            self.current_turn_count = 0
            debug_write("Performing turn {}.".format(self.turn_idx))
            self.submit_turn()

            stateType = 1
            while stateType == 1:
                game_state_string = self.get_command()
                state = json.loads(game_state_string)
                stateType = int(state.get("turnInfo")[0])

            if stateType == 0:
                debug_write("Got new game state. Updating Gym wrapper state.")
                self.game_state = gamelib.GameState(self.config, game_state_string)
                self.env_state = self.convert_game_state_to_env_state(self.game_state)
            elif stateType == 2:
                debug_write("Got end state, game over. Stopping algo.")
                self.done = True
            self.turn_idx += 1
            reward = self.calculate_reward(self.game_state)
        else:
            self.current_turn_count += 1
            x, y, unit, action_ = self.parse_action(action)

            if action_ == 0:  # Place
                if self.game_state.attempt_spawn(unit, [x, y], num=1):  # If successfully spawned
                    self.env_state[x][y][self.unit_to_int[unit]] += 1
            elif action_ == 1:  # Upgrade
                if self.game_state.attempt_upgrade([x, y]):  # If successfully spawned
                    for unit in range(self.NUM_UNIT_TYPES):
                        if self.env_state[x][y][unit]:
                            self.env_state[x][y][unit] += 1
            elif action_ == 2:  # Delete
                if self.game_state.attempt_remove([x, y]):  # If successfully spawned
                    self.env_state[x][y] = 0
            reward = 0.0

        return self.env_state, reward, self.done, {"episode":None, "is_success":None}

    def parse_action(self, action):
        from random import randrange
        x,y = randrange(27), randrange(13)
        # x, y = None, None  # TODO: Calculate x, y
        unit = None
        action_ = None
        offset = 0

        if action < 673:  # Create Stationary Unit
            action_ = self.CREATE_ACTION

            # Stationary units
            if action < 197: # 0-196
                unit = self.WALL
                offset = 0
            elif action < 393: # 197 - 392
                unit = self.SUPPORT
                offset = action - 197
            elif action < 589: # 393 - 588
                unit = self.TURRET
                offset = action - 393

            # Mobile units
            elif action < 617: # 589 - 616
                unit = self.SCOUT
                offset = action - 589
            elif action < 645: # 617 - 644
                unit = self.DEMOLISHER
                offset = action - 617
            else: # 645 - 672 # TODO: check offsets
                unit = self.INTERCEPTOR
                offset = action - 645

        elif action < 869:  # Upgrade unit (67)
            action_ = self.UPGRADE_ACTION
            offset = action - 672
        else: # (action < 1064), Delete unit
            action_ = self.DELETE_ACTION
            offset = action - 869

        x, y = self.COORD_MAP[offset]
        return x, y, unit, action_

    def calculate_reward(self, game_state):
        return game_state.my_health - game_state.enemy_health

    def close(self):
        self.stop_engine()

if __name__=='__main__':
    env = TerminalGymWrapper()

    # First
    done = False
    observation = env.reset()
    while not done:
        action = 0
        observation, reward, done, info = env.step(action)

    # Second
    done = False
    observation = env.reset()
    while not done:
        action = 0
        observation, reward, done, info = env.step(action)

    env.stop_engine()
    debug_write("Completed")

