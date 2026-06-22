import time
import random

def profile_agent():
    import main
    
    class MockObs:
        def __init__(self, step=100, player=0, planets=None, fleets=None, angular_velocity=0.025):
            self.step = step
            self.player = player
            self.angular_velocity = angular_velocity
            self.planets = planets or []
            self.fleets = fleets or []
            self.comet_planet_ids = []
        def get(self, key, default=None): return getattr(self, key, default)

    class MockConfig: pass
    
    planets = []
    for i in range(20):
        planets.append([i, random.randint(-1, 3), random.randint(10, 90), random.randint(10, 90), 5, 100, 5])
        
    fleets = []
    for i in range(200):
        fleets.append([i, random.randint(0, 3), random.randint(10, 90), random.randint(10, 90), random.random() * 6.28, 0, random.randint(10, 50)])
        
    obs = MockObs(planets=planets, fleets=fleets)
    
    start = time.time()
    for _ in range(10): # Simulate 10 steps
        main.agent(obs, MockConfig())
    end = time.time()
    
    print(f"Time per step with 20 planets and 200 fleets: {(end - start) / 10:.4f} seconds")

if __name__ == "__main__":
    profile_agent()
