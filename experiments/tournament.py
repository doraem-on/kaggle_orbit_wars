import sys
import os
import random
import time
from multiprocessing import Pool

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from agent import agent
from simulator import Simulator
from world_model import GameState
from tools.match_runner import MatchObs, sim_to_obs

def generate_random_board(seed):
    rng = random.Random(seed)
    planets = [
        [0, 0, 20, 50, 5, 100, 5],
        [1, 1, 80, 50, 5, 100, 5]
    ]
    
    num_pairs = rng.randint(2, 5)
    p_id = 2
    for _ in range(num_pairs):
        # Generate in left half
        x = rng.randint(10, 45)
        y = rng.randint(10, 90)
        radius = rng.randint(2, 4)
        ships = rng.randint(5, 40)
        prod = rng.randint(1, 4)
        
        # Add left
        planets.append([p_id, -1, x, y, radius, ships, prod])
        p_id += 1
        # Add right (symmetric)
        planets.append([p_id, -1, 100 - x, 100 - y, radius, ships, prod])
        p_id += 1
        
    return planets

def run_single_match(args):
    seed, config_p0, config_p1, max_turns = args
    planets = generate_random_board(seed)
    
    init_obs = MatchObs(0, 0, planets, [])
    initial_state_p0 = GameState(init_obs, config_p0) # Used to just initialize sim
    sim = Simulator(initial_state_p0)
    
    idle_ships_p0 = 0
    idle_ships_p1 = 0
    
    for turn in range(max_turns):
        obs_p0 = sim_to_obs(sim, 0)
        obs_p1 = sim_to_obs(sim, 1)
        
        actions_p0 = agent(obs_p0, config_p0)
        actions_p1 = agent(obs_p1, config_p1)
        
        for a in actions_p0:
            sim.add_launch(a[0], a[1], a[2])
        for a in actions_p1:
            sim.add_launch(a[0], a[1], a[2])
            
        sim._step()
        sim.step += 1
        
        # Metrics: Track idle ships
        for p in sim.planets.values():
            if p["owner"] == 0:
                idle_ships_p0 += p["ships"]
            elif p["owner"] == 1:
                idle_ships_p1 += p["ships"]
        
        p0_alive = any(p["owner"] == 0 for p in sim.planets.values()) or any(f["owner"] == 0 for f in sim.fleets)
        p1_alive = any(p["owner"] == 1 for p in sim.planets.values()) or any(f["owner"] == 1 for f in sim.fleets)
        
        if not p0_alive or not p1_alive:
            break
            
    p0_score = sum(p["production"] for p in sim.planets.values() if p["owner"] == 0)
    p1_score = sum(p["production"] for p in sim.planets.values() if p["owner"] == 1)
    
    winner = -1
    if p0_score > p1_score:
        winner = 0
    elif p1_score > p0_score:
        winner = 1
        
    return {
        "winner": winner,
        "turns": sim.step,
        "idle_p0": idle_ships_p0 / max(1, sim.step),
        "idle_p1": idle_ships_p1 / max(1, sim.step)
    }

class TournamentRunner:
    def __init__(self, num_games=10, max_turns=300):
        self.num_games = num_games
        self.max_turns = max_turns
        
    def run(self, config_p0, config_p1):
        seeds = [random.randint(0, 999999) for _ in range(self.num_games)]
        args = [(seed, config_p0, config_p1, self.max_turns) for seed in seeds]
        
        p0_wins = 0
        p1_wins = 0
        draws = 0
        
        avg_turns = 0
        avg_idle_p0 = 0
        avg_idle_p1 = 0
        
        start_time = time.time()
        
        with Pool() as pool:
            results = pool.map(run_single_match, args)
            
        for res in results:
            if res["winner"] == 0:
                p0_wins += 1
            elif res["winner"] == 1:
                p1_wins += 1
            else:
                draws += 1
                
            avg_turns += res["turns"]
            avg_idle_p0 += res["idle_p0"]
            avg_idle_p1 += res["idle_p1"]
            
        n = self.num_games
        print(f"Tournament Finished in {time.time() - start_time:.2f}s")
        print(f"P0 Wins: {p0_wins} ({p0_wins/n*100:.1f}%)")
        print(f"P1 Wins: {p1_wins} ({p1_wins/n*100:.1f}%)")
        print(f"Draws: {draws}")
        print(f"Avg Turns: {avg_turns/n:.1f}")
        print(f"Avg Idle Ships (P0): {avg_idle_p0/n:.1f}")
        print(f"Avg Idle Ships (P1): {avg_idle_p1/n:.1f}")
        
        return p0_wins / n

if __name__ == "__main__":
    smart_swarm = {
        "deduplicate_targets": True,
        "max_targets": 5
    }
    old_robust_bot = {
        "deduplicate_targets": True, # Deduplication doesn't matter for max_targets=1
        "max_targets": 1
    }
    
    runner = TournamentRunner(num_games=10)
    print("Running Verification Tournament: Smart Swarm vs Old Robust Bot...")
    print("P0: Smart Swarm (max_targets=5)")
    print("P1: Old Robust Bot (max_targets=1)")
    runner.run(smart_swarm, old_robust_bot)
