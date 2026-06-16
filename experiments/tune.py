import os
import json
import random
from tournament import TournamentRunner

LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "leaderboard.json")

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r") as f:
            return json.load(f)
    return {
        "best_config": {},
        "history": []
    }

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_random_config():
    return {
        "defense_score_multiplier": random.uniform(20.0, 100.0),
        "attack_score_multiplier": random.uniform(5.0, 40.0),
        "defense_buffer_ships": random.randint(0, 10),
        "reserve_ships_min": random.randint(0, 15)
    }

def tune(iterations=10, games_per_eval=20):
    lb = load_leaderboard()
    baseline_config = lb.get("best_config", {})
    
    print(f"Starting Tuning Session: {iterations} variants, {games_per_eval} games each.")
    print(f"Current Baseline: {baseline_config}")
    
    runner = TournamentRunner(num_games=games_per_eval, max_turns=300)
    
    best_winrate = 0.50 # Must beat 50% to be considered better
    best_new_config = None
    
    for i in range(iterations):
        candidate = get_random_config()
        print(f"\n--- Testing Variant {i+1}/{iterations} ---")
        print(json.dumps(candidate, indent=2))
        
        # P0 is candidate, P1 is baseline
        winrate = runner.run(candidate, baseline_config)
        
        lb["history"].append({
            "iteration": i,
            "config": candidate,
            "winrate": winrate
        })
        
        if winrate > best_winrate:
            print(f"*** NEW BEST VARIANT FOUND! Winrate: {winrate*100:.1f}% ***")
            best_winrate = winrate
            best_new_config = candidate
            
    if best_new_config:
        print("\n===============================")
        print(f"Tuning Complete! Upgrading Baseline.")
        print(f"New Winrate: {best_winrate*100:.1f}%")
        print("New Config:", json.dumps(best_new_config, indent=2))
        lb["best_config"] = best_new_config
    else:
        print("\n===============================")
        print("Tuning Complete. No variant beat the baseline.")
        
    save_leaderboard(lb)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    
    if args.test:
        tune(iterations=2, games_per_eval=4)
    else:
        tune(iterations=10, games_per_eval=50)
