import sys
import json
import time

def run_match_subprocess(p0_type, p1_type, seed):
    # Depending on p0_type and p1_type, we load the correct planner
    # We must do this dynamically to avoid import caching
    
    # Setup board
    import random
    random.seed(seed)
    planets = []
    p0_x = random.randint(10, 30)
    p0_y = random.randint(20, 80)
    planets.append([0, 0, p0_x, p0_y, 5, 100, 5])
    planets.append([1, 1, 100 - p0_x, 100 - p0_y, 5, 100, 5])
    for i in range(8):
        planets.append([2 + i, -1, random.randint(10, 90), random.randint(10, 90), random.randint(2, 5), random.randint(10, 40), random.randint(2, 5)])
        
    class MockConfig: pass
    config = MockConfig()
    config.episodeSteps = 300
    
    class MockObs:
        def __init__(self, step=0, player=0, planets=None, fleets=None, angular_velocity=0.025):
            self.step = step
            self.player = player
            self.angular_velocity = angular_velocity
            self.planets = planets or []
            self.fleets = fleets or []
            self.comet_planet_ids = []
        def get(self, key, default=None): return getattr(self, key, default)

    if "old" in [p0_type, p1_type]:
        sys.path.insert(0, "./old_bot")
        from old_bot.planner import BeamSearchPlanner as OldBSP
        from old_bot.world_model import GameState as OldGS
        from old_bot.simulator import Simulator as OldSim
        sys.path.pop(0)
        
        # Clear modules so new imports work perfectly independent of old bot
        to_del = [k for k in sys.modules if k in ("evaluator", "planner", "simulator", "world_model", "constants", "geometry")]
        for k in to_del: del sys.modules[k]

    from planner import GreedyPlanner as NewGOP
    from mcts_planner import MCTSPlanner as NewMCTS
    from world_model import GameState as NewGS
    from simulator import Simulator as NewSim

    sim = NewSim(NewGS(MockObs(step=0, player=0, planets=planets, fleets=[]), config))
    sim.fleets = []
    
    new_weights = {}
    try:
        with open("best_weights.json", "r") as f:
            new_weights = json.load(f)
    except: pass
        
    for step in range(300):
        plist = [[p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]] for p in sim.planets.values()]
        flist = [[f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]] for f in sim.fleets]
        
        # P0
        if p0_type == "new":
            s0 = NewGS(MockObs(step=step, player=0, planets=plist, fleets=flist), config)
            s0.params.update(new_weights)
            a0 = NewGOP(s0).generate_moves() if step < 16 else NewMCTS(s0, max_time=0.1).generate_moves()
        else:
            sys.path.insert(0, "./old_bot")
            from old_bot.planner import BeamSearchPlanner as OldBSP_local
            from old_bot.world_model import GameState as OldGS_local
            sys.path.pop(0)
            s0 = OldGS_local(MockObs(step=step, player=0, planets=plist, fleets=flist), config)
            a0 = OldBSP_local(s0, max_time=0.1).generate_moves()
            
        # P1
        if p1_type == "new":
            s1 = NewGS(MockObs(step=step, player=1, planets=plist, fleets=flist), config)
            s1.params.update(new_weights)
            a1 = NewGOP(s1).generate_moves() if step < 16 else NewMCTS(s1, max_time=0.1).generate_moves()
        else:
            sys.path.insert(0, "./old_bot")
            from old_bot.planner import BeamSearchPlanner as OldBSP_local
            from old_bot.world_model import GameState as OldGS_local
            sys.path.pop(0)
            s1 = OldGS_local(MockObs(step=step, player=1, planets=plist, fleets=flist), config)
            a1 = OldBSP_local(s1, max_time=0.1).generate_moves()
            
        for act in a0: sim.add_launch(act[0], act[1], act[2])
        for act in a1: sim.add_launch(act[0], act[1], act[2])
        
        sim._step()
        sim.step += 1
        
        p0_alive = any(p["owner"] == 0 for p in sim.planets.values()) or any(f["owner"] == 0 for f in sim.fleets)
        p1_alive = any(p["owner"] == 1 for p in sim.planets.values()) or any(f["owner"] == 1 for f in sim.fleets)
        if not p0_alive: return 1
        if not p1_alive: return 0
        
    p0_s = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 0) + sum(f["ships"] for f in sim.fleets if f["owner"] == 0)
    p1_s = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 1) + sum(f["ships"] for f in sim.fleets if f["owner"] == 1)
    
    if p0_s > p1_s: return 0
    if p1_s > p0_s: return 1
    return 0.5

if __name__ == "__main__":
    p0 = sys.argv[1]
    p1 = sys.argv[2]
    seed = int(sys.argv[3])
    res = run_match_subprocess(p0, p1, seed)
    print(res)
