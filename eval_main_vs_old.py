import multiprocessing
import random
import sys

def worker(seed):
    import sys
    sys.path.insert(0, ".")
    from simulator import Simulator
    from world_model import GameState
    import importlib
    
    # Reload main agent safely
    import main
    importlib.reload(main)
    from main import agent as main_agent

    # Load Old BSP
    sys.path.insert(0, "./old_bot")
    from old_bot.planner import BeamSearchPlanner as OldBSP
    from old_bot.world_model import GameState as OldGS
    sys.path.pop(0)

    class MockObs:
        def __init__(self, step=0, player=0, planets=None, fleets=None, angular_velocity=0.025):
            self.step = step
            self.player = player
            self.angular_velocity = angular_velocity
            self.planets = planets or []
            self.fleets = fleets or []
            self.comet_planet_ids = []
        def get(self, key, default=None): return getattr(self, key, default)

    class MockConfig: pass
    config = MockConfig()
    
    random.seed(seed)
    planets = []
    p0_x = random.randint(10, 30)
    p0_y = random.randint(20, 80)
    planets.append([0, 0, p0_x, p0_y, 5, 100, 5])
    planets.append([1, 1, 100 - p0_x, 100 - p0_y, 5, 100, 5])
    for i in range(8):
        planets.append([2 + i, -1, random.randint(10, 90), random.randint(10, 90), random.randint(2, 5), random.randint(10, 40), random.randint(2, 5)])
        
    obs = MockObs(step=0, player=0, planets=planets, fleets=[])
    state = GameState(obs, config)
    sim = Simulator(state)
    sim.fleets = []
    
    try:
        for step in range(300):
            plist = [[p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]] for p in sim.planets.values()]
            flist = [[f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]] for f in sim.fleets]
            
            # P0: main.py
            obs0 = MockObs(step=step, player=0, planets=plist, fleets=flist)
            acts0 = main_agent(obs0, config)
            if acts0 is None: acts0 = []
            
            # P1: Old BSP
            obs1 = MockObs(step=step, player=1, planets=plist, fleets=flist)
            s1 = OldGS(obs1, config)
            acts1 = OldBSP(s1, max_time=0.1).generate_moves()
            if acts1 is None: acts1 = []
            
            for act in acts0: sim.add_launch(act[0], act[1], act[2])
            for act in acts1: sim.add_launch(act[0], act[1], act[2])
            
            sim._step()
            sim.step += 1
            
            p0_alive = any(p["owner"] == 0 for p in sim.planets.values()) or any(f["owner"] == 0 for f in sim.fleets)
            p1_alive = any(p["owner"] == 1 for p in sim.planets.values()) or any(f["owner"] == 1 for f in sim.fleets)
            if not p0_alive: return 1 # P1 wins
            if not p1_alive: return 0 # P0 wins
            
        p0_s = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 0) + sum(f["ships"] for f in sim.fleets if f["owner"] == 0)
        p1_s = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 1) + sum(f["ships"] for f in sim.fleets if f["owner"] == 1)
        
        if p0_s > p1_s: return 0
        if p1_s > p0_s: return 1
        return 0.5
    except Exception as e:
        return f"CRASH: {str(e)}"

if __name__ == "__main__":
    print("Running main.py vs Old BSP over 50 matches...")
    pool = multiprocessing.Pool(processes=min(10, multiprocessing.cpu_count()))
    results = pool.map(worker, range(50))
    
    main_wins = results.count(0)
    old_wins = results.count(1)
    ties = results.count(0.5)
    crashes = len([r for r in results if isinstance(r, str) and r.startswith("CRASH")])
    
    print(f"main.py (Fixed Heuristic) Wins: {main_wins}")
    print(f"Old BSP (561-Elo) Wins: {old_wins}")
    print(f"Ties: {ties}")
    if crashes > 0:
        print(f"CRASHES: {crashes}")
