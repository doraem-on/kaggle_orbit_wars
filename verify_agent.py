import time
import json
from agent import agent

# Create a mock observation
# planets: [[id, owner, x, y, radius, ships, production], ...]
# fleets: [[id, owner, x, y, angle, from_planet_id, ships], ...]
class MockObs:
    def __init__(self):
        self.step = 400
        self.player = 0
        self.angular_velocity = 0.025
        self.planets = [
            [0, 0, 80, 80, 5, 50, 5],
            [1, 1, 20, 20, 5, 50, 5],
            [2, -1, 40, 40, 3, 10, 2],
            [3, -1, 60, 60, 3, 10, 2]
        ]
        self.fleets = [
            [0, 0, 75, 75, 3.14, 0, 20]
        ]
        self.comets = []
        self.comet_planet_ids = []
        
    def get(self, key, default=None):
        return getattr(self, key, default)

class MockConfig:
    pass

def main():
    obs = MockObs()
    config = MockConfig()
    
    start = time.time()
    actions = agent(obs, config)
    end = time.time()
    
    print(f"Agent executed in {end - start:.5f} seconds.")
    print(f"Generated {len(actions)} actions:")
    for a in actions:
        print(f" - {a}")

if __name__ == "__main__":
    main()
