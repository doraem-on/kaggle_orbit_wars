import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from world_model import GameState
from simulator import Simulator

class DummyObs:
    def __init__(self):
        self.step = 0
        self.player = 0
        self.angular_velocity = 0.05
        # id, owner, x, y, radius, ships, production
        self.planets = [
            [0, 0, 10, 10, 2, 50, 3],
            [1, 1, 90, 90, 2, 50, 3]
        ]
        self.fleets = []
        
    def get(self, key, default):
        if key == "comets":
            return []
        if key == "comet_planet_ids":
            return []
        return default

class TestSimulator(unittest.TestCase):
    def test_basic_simulation(self):
        obs = DummyObs()
        state = GameState(obs, {})
        sim = Simulator(state)
        
        sim.simulate_ahead(5)
        # 5 turns * 3 production = +15 ships
        self.assertEqual(sim.planets[0]["ships"], 65)
        self.assertEqual(sim.planets[1]["ships"], 65)

if __name__ == '__main__':
    unittest.main()
