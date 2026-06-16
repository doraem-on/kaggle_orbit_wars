import multiprocessing
import random
import time
import json
import math
import copy

from world_model import GameState
from planner import BeamSearchPlanner, GreedyOpeningPlanner
from simulator import Simulator

class MockObs:
    def __init__(self, step=0, player=0, planets=None, fleets=None, angular_velocity=0.025):
        self.step = step
        self.player = player
        self.angular_velocity = angular_velocity
        self.planets = planets or []
        self.fleets = fleets or []
        self.comet_planet_ids = []
    def get(self, key, default=None):
        return getattr(self, key, default)

class MockConfig:
    pass

def generate_random_board(seed):
    random.seed(seed)
    planets = []
    # Home planets (can be symmetric or asymmetric, let's keep them symmetric for balance)
    p0_x = random.randint(10, 30)
    p0_y = random.randint(20, 80)
    planets.append([0, 0, p0_x, p0_y, 5, 100, 5])
    planets.append([1, 1, 100 - p0_x, 100 - p0_y, 5, 100, 5])
    
    # ASYMMETRIC neutral planets
    for i in range(8):
        nx = random.randint(10, 90)
        ny = random.randint(10, 90)
        prod = random.randint(2, 5)
        ships = random.randint(10, 40)
        planets.append([2 + i, -1, nx, ny, prod, ships, prod])
        
    return planets

def run_match(weights_p0, weights_p1, seed=0, max_turns=300):
    # Setup initial random symmetric board
    planets = generate_random_board(seed)
    
    # We use Simulator as the game engine
    config = MockConfig()
    config.episodeSteps = max_turns
    
    dummy_obs = MockObs(step=0, player=0, planets=planets, fleets=[])
    dummy_state = GameState(dummy_obs, config)
    sim = Simulator(dummy_state)
    sim.fleets = [] # clear fake opponent model fleets
    
    for step in range(max_turns):
        # Build obs
        plist = [[p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]] for p in sim.planets.values()]
        flist = [[f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]] for f in sim.fleets]
        
        # Player 0 acts
        obs_p0 = MockObs(step=step, player=0, planets=plist, fleets=flist)
        state_p0 = GameState(obs_p0, config)
        state_p0.params.update(weights_p0)
        
        if step < 16:
            actions_p0 = GreedyOpeningPlanner(state_p0).generate_moves()
        else:
            actions_p0 = BeamSearchPlanner(state_p0, max_time=0.1).generate_moves() # Fast search for tuning
            
        # Player 1 acts
        obs_p1 = MockObs(step=step, player=1, planets=plist, fleets=flist)
        state_p1 = GameState(obs_p1, config)
        state_p1.params.update(weights_p1)
        
        if step < 16:
            actions_p1 = GreedyOpeningPlanner(state_p1).generate_moves()
        else:
            actions_p1 = BeamSearchPlanner(state_p1, max_time=0.1).generate_moves()
            
        # Apply actions
        for act in actions_p0:
            sim.add_launch(act[0], act[1], act[2])
        for act in actions_p1:
            sim.add_launch(act[0], act[1], act[2])
            
        sim._step()
        sim.step += 1
        
        # Check end condition
        p0_alive = any(p["owner"] == 0 for p in sim.planets.values()) or any(f["owner"] == 0 for f in sim.fleets)
        p1_alive = any(p["owner"] == 1 for p in sim.planets.values()) or any(f["owner"] == 1 for f in sim.fleets)
        
        if not p0_alive: return 1
        if not p1_alive: return 0
        
    # Evaluate score
    p0_ships = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 0) + sum(f["ships"] for f in sim.fleets if f["owner"] == 0)
    p1_ships = sum(p["ships"] for p in sim.planets.values() if p["owner"] == 1) + sum(f["ships"] for f in sim.fleets if f["owner"] == 1)
    
    if p0_ships > p1_ships: return 0
    elif p1_ships > p0_ships: return 1
    return 0.5

def worker(args):
    w0, w1, seed = args
    return run_match(w0, w1, seed)

def mutate_weights(base_weights):
    new_weights = copy.deepcopy(base_weights)
    key = random.choice(list(new_weights.keys()))
    # Mutate by +/- 10%
    new_weights[key] *= random.uniform(0.9, 1.1)
    return new_weights

if __name__ == "__main__":
    baseline_weights = {
        "alpha": 15.0,
        "beta": 0.5,
        "gamma": 2.0,
        "early_prod": 25.0,
        "mid_def": 15.0,
        "late_agg": 25.0
    }
    
    import os
    if os.path.exists("best_weights.json"):
        try:
            with open("best_weights.json", "r") as f:
                baseline_weights = json.load(f)
            print(">>> Loaded previous best_weights.json!")
        except Exception as e:
            pass
            
    print("Starting Continuous Local Tuning Engine on 10 Cores...")
    pool = multiprocessing.Pool(processes=10)
    
    iteration = 1
    best_weights = baseline_weights
    
    # Run indefinitely to continuously improve weights
    while True:
        challenger = mutate_weights(best_weights)
        print(f"\n[Iteration {iteration}] Testing Challenger: {challenger}")
        
        # P0=Challenger, P1=Baseline and P0=Baseline, P1=Challenger (fairness)
        jobs = []
        for i in range(5):
            jobs.append((challenger, best_weights, i)) # Challenger is P0
            jobs.append((best_weights, challenger, i)) # Challenger is P1
            
        results = pool.map(worker, jobs)
        
        challenger_wins = 0
        for i, res in enumerate(results):
            if i % 2 == 0 and res == 0: challenger_wins += 1 # Challenger was P0 and won
            if i % 2 == 1 and res == 1: challenger_wins += 1 # Challenger was P1 and won
            if res == 0.5: challenger_wins += 0.5
            
        print(f"Challenger Win Rate: {challenger_wins}/10")
        if challenger_wins > 5:
            print(">>> NEW CHAMPION! Saving weights.")
            best_weights = challenger
            with open("best_weights.json", "w") as f:
                json.dump(best_weights, f)
        
        iteration += 1
        
    print("\n[Tuning completed successfully.]")
    pool.close()
    pool.join()
