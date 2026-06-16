import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent import agent
from simulator import Simulator
from world_model import GameState
from constants import MAX_TURNS

class MatchObs:
    def __init__(self, step, player, planets, fleets, comets=None, comet_ids=None):
        self.step = step
        self.player = player
        self.angular_velocity = 0.025
        self.planets = planets
        self.fleets = fleets
        self.comets = comets or []
        self.comet_planet_ids = comet_ids or []
        
    def get(self, key, default=None):
        return getattr(self, key, default)

class MockConfig:
    pass

def sim_to_obs(sim, player_id):
    planets_data = []
    comet_ids = []
    for p in sim.planets.values():
        planets_data.append([
            p["id"], p["owner"], p["x"], p["y"], p["radius"], p["ships"], p["production"]
        ])
        if p.get("is_comet"):
            comet_ids.append(p["id"])
            
    fleets_data = []
    for f in sim.fleets:
        fleets_data.append([
            f["id"], f["owner"], f["x"], f["y"], f["angle"], 0, f["ships"]
        ])
        
    return MatchObs(sim.step, player_id, planets_data, fleets_data, [], comet_ids)

def run_match():
    # Setup initial symmetric board
    planets = [
        # Player 0 home
        [0, 0, 20, 50, 5, 100, 5],
        # Player 1 home
        [1, 1, 80, 50, 5, 100, 5],
        # High production neutrals
        [2, -1, 50, 20, 4, 30, 4],
        [3, -1, 50, 80, 4, 30, 4],
        # Low production neutrals
        [4, -1, 35, 35, 3, 10, 2],
        [5, -1, 65, 65, 3, 10, 2],
        [6, -1, 35, 65, 3, 10, 2],
        [7, -1, 65, 35, 3, 10, 2]
    ]
    
    init_obs = MatchObs(0, 0, planets, [])
    config = MockConfig()
    initial_state = GameState(init_obs, config)
    sim = Simulator(initial_state)
    
    history = []
    
    print("Starting Match...")
    for turn in range(300): # Cap at 300 for quick testing
        # Get actions for both players
        obs_p0 = sim_to_obs(sim, 0)
        obs_p1 = sim_to_obs(sim, 1)
        
        # Save state for replay
        history.append({
            "step": sim.step,
            "planets": obs_p0.planets,
            "fleets": obs_p0.fleets
        })
        
        # In a real setup, we might have agent1 and agent2
        # Here we just run the same agent against itself
        actions_p0 = agent(obs_p0, config)
        actions_p1 = agent(obs_p1, config)
        
        # Apply actions
        for a in actions_p0:
            sim.add_launch(a[0], a[1], a[2])
        for a in actions_p1:
            sim.add_launch(a[0], a[1], a[2])
            
        # Step environment
        sim._step()
        sim.step += 1
        
        # Fast termination if someone lost all planets and ships
        p0_alive = any(p["owner"] == 0 for p in sim.planets.values()) or any(f["owner"] == 0 for f in sim.fleets)
        p1_alive = any(p["owner"] == 1 for p in sim.planets.values()) or any(f["owner"] == 1 for f in sim.fleets)
        
        if not p0_alive or not p1_alive:
            print(f"Match ended early at turn {turn}.")
            break
            
    # Determine winner
    p0_score = sum(p["production"] for p in sim.planets.values() if p["owner"] == 0)
    p1_score = sum(p["production"] for p in sim.planets.values() if p["owner"] == 1)
    
    print(f"Match Finished. Total Turns: {sim.step}")
    print(f"Player 0 Production: {p0_score}")
    print(f"Player 1 Production: {p1_score}")
    if p0_score > p1_score:
        print("Winner: Player 0")
    elif p1_score > p0_score:
        print("Winner: Player 1")
    else:
        print("Draw")
        
    with open("replay.json", "w") as f:
        json.dump(history, f)
    print("Saved replay to replay.json")

if __name__ == "__main__":
    run_match()
