import multiprocessing
import random
import time
from simulator import Simulator
from world_model import GameState

class MockObs:
    def __init__(self, step=0, player=0, planets=None, fleets=None, angular_velocity=0.025):
        self.step = step
        self.player = player
        self.angular_velocity = angular_velocity
        self.planets = planets or []
        self.fleets = fleets or []
        self.comets = []
        self.comet_planet_ids = []
    def get(self, key, default=None): return getattr(self, key, default)

class MockConfig: pass

def worker(seed):
    import sys
    sys.path.insert(0, ".")
    from main import agent

    random.seed(seed)
    planets = []
    for i in range(4):
        # 4 players
        px = random.randint(10, 90)
        py = random.randint(10, 90)
        planets.append([i, i, px, py, 5, 100, 5])
    
    for i in range(16):
        # 16 neutrals
        px = random.randint(10, 90)
        py = random.randint(10, 90)
        planets.append([4+i, -1, px, py, random.randint(2, 5), random.randint(10, 30), random.randint(1, 4)])

    config = MockConfig()
    obs = MockObs(step=0, player=0, planets=planets, fleets=[])
    state = GameState(obs, config)
    sim = Simulator(state)
    sim.fleets = []
    
    try:
        for step in range(400):
            plist = [[p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]] for p in sim.planets.values()]
            flist = [[f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]] for f in sim.fleets]
            
            all_actions = []
            for pid in range(4):
                p_obs = MockObs(step=step, player=pid, planets=plist, fleets=flist)
                start = time.time()
                acts = agent(p_obs, config)
                if time.time() - start > 2.0:
                    return f"TIMEOUT on step {step}"
                if acts is None:
                    acts = []
                all_actions.extend(acts)
                
            for act in all_actions:
                sim.add_launch(act[0], act[1], act[2])
            sim._step()
            sim.step += 1
        return "SUCCESS"
    except Exception as e:
        return f"CRASH: {str(e)}"

if __name__ == "__main__":
    print("Starting CPU-Intensive Multiprocessing Validation for main.py...")
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    jobs = range(100)
    results = pool.map(worker, jobs)
    
    success = results.count("SUCCESS")
    print(f"\\n--- STRESS TEST RESULTS ---")
    print(f"Total Matches Run: 100 (40,000 total simulation steps)")
    print(f"Successful Matches (No crashes/timeouts): {success}")
    if success < 100:
        failures = [r for r in results if r != "SUCCESS"]
        print(f"Failures: {set(failures)}")
    else:
        print("✅ 100% SUCCESS RATE. NO CRASHES. NO TIMEOUTS.")
