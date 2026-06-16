import json
import time
from world_model import GameState
from simulator import Simulator
from planner import BeamSearchPlanner, GreedyOpeningPlanner

class MockObs:
    def __init__(self, step=0, player=0, planets=None, fleets=None, angular_velocity=0.025):
        self.step = step
        self.player = player
        self.angular_velocity = angular_velocity
        self.planets = planets or []
        self.fleets = fleets or []
        self.comets = []
        self.comet_planet_ids = []
    def get(self, key, default=None):
        return getattr(self, key, default)

class MockConfig:
    pass

def run_ffa():
    # 4 player symmetric board
    planets = [
        # Player Homes
        [0, 0, 10, 10, 5, 100, 5],
        [1, 1, 90, 10, 5, 100, 5],
        [2, 2, 10, 90, 5, 100, 5],
        [3, 3, 90, 90, 5, 100, 5],
        
        # High value center planets
        [4, -1, 35, 35, 4, 30, 4],
        [5, -1, 65, 35, 4, 30, 4],
        [6, -1, 35, 65, 4, 30, 4],
        [7, -1, 65, 65, 4, 30, 4],
        
        # Neutrals
        [8, -1, 50, 20, 3, 15, 2],
        [9, -1, 50, 80, 3, 15, 2],
        [10, -1, 20, 50, 3, 15, 2],
        [11, -1, 80, 50, 3, 15, 2],
    ]
    
    baseline_weights = {
        "alpha": 15.0, "beta": 0.5, "gamma": 2.0,
        "early_prod": 25.0, "mid_def": 15.0, "late_agg": 25.0
    }
    
    with open("best_weights.json", "r") as f:
        tuned_weights = json.load(f)
        
    config = MockConfig()
    config.episodeSteps = 400
    
    dummy_obs = MockObs(step=0, player=0, planets=planets, fleets=[])
    dummy_state = GameState(dummy_obs, config)
    sim = Simulator(dummy_state)
    sim.fleets = []
    
    print("Starting 4-Player Free-For-All Simulation (400 Turns)")
    print("Player 0: TUNED CHAMPION BOT")
    print("Player 1, 2, 3: Original Baseline Bots\n")
    
    start_time = time.time()
    
    for step in range(400):
        if step % 50 == 0:
            print(f"Step {step}/400...")
            
        plist = [[p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]] for p in sim.planets.values()]
        flist = [[f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]] for f in sim.fleets]
        
        all_actions = []
        for player_id in range(4):
            # Check if player is alive
            alive = any(p["owner"] == player_id for p in sim.planets.values()) or any(f["owner"] == player_id for f in sim.fleets)
            if not alive:
                continue
                
            obs = MockObs(step=step, player=player_id, planets=plist, fleets=flist)
            state = GameState(obs, config)
            
            # Player 0 gets tuned weights, others get baseline
            if player_id == 0:
                state.params.update(tuned_weights)
            else:
                state.params.update(baseline_weights)
                
            if step < 15:
                acts = GreedyOpeningPlanner(state).generate_moves()
            else:
                acts = BeamSearchPlanner(state, max_time=0.1).generate_moves()
            all_actions.extend(acts)
            
        for act in all_actions:
            sim.add_launch(act[0], act[1], act[2])
            
        sim._step()
        sim.step += 1
        
    print("\n--- FINAL RESULTS ---")
    scores = {0: 0, 1: 0, 2: 0, 3: 0}
    for p in sim.planets.values():
        if p["owner"] in scores:
            scores[p["owner"]] += p["ships"]
    for f in sim.fleets:
        if f["owner"] in scores:
            scores[f["owner"]] += f["ships"]
            
    print(f"Player 0 (Tuned Champion): {scores[0]} ships")
    print(f"Player 1 (Baseline):       {scores[1]} ships")
    print(f"Player 2 (Baseline):       {scores[2]} ships")
    print(f"Player 3 (Baseline):       {scores[3]} ships")
    
    winner = max(scores, key=scores.get)
    if winner == 0:
        print("\n🏆 TUNED CHAMPION ABSOLUTELY DOMINATED THE FFA! 🏆")
    else:
        print(f"\nPlayer {winner} won the FFA.")
        
if __name__ == "__main__":
    run_ffa()
