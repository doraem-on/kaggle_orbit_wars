import json
import os

def analyze_replay():
    if not os.path.exists("replay.json"):
        print("No replay.json found.")
        return
        
    with open("replay.json", "r") as f:
        replay = json.load(f)
        
    print("--- REPLAY ANALYSIS ---")
    
    # 1. Check for crashes/errors
    crashes = []
    # If replay is a dict with steps, use it. Otherwise, assume it's a list of steps directly.
    steps = replay.get("steps", []) if isinstance(replay, dict) else replay
    
    for i, step in enumerate(steps):
        # Depending on the Kaggle env version, step might be a list of player dicts, or a dict.
        if isinstance(step, list):
            for p_idx, player_state in enumerate(step):
                status = player_state.get("status")
                if status and status not in ("DONE", "ACTIVE"):
                    crashes.append((i, p_idx, status))
                    
    if crashes:
        print("\n[!] CRASHES/ERRORS DETECTED:")
        for turn, p_idx, status in crashes:
            print(f"  - Turn {turn}, Player {p_idx} ended with status: {status}")
    else:
        print("\n[+] No crashes detected. Bot survived to the end.")
        
    # 2. Check final scores
    if len(steps) > 0:
        last_step = steps[-1]
        if isinstance(last_step, list) and len(last_step) >= 2:
            print(f"\nFinal Rewards (Player 0 vs Player 1): {last_step[0].get('reward')} vs {last_step[1].get('reward')}")
        
    # 3. Analyze Expansion/Ship counts over time (sampled every 50 turns)
    print("\n[+] Game Progression (every 50 turns):")
    for i, step in enumerate(steps):
        if i % 50 == 0 or i == len(steps) - 1:
            obs = step[0].get("observation", {}) if isinstance(step, list) else step
            
            # Extract from raw arrays instead of dict if orbit_wars uses arrays
            if "planets" in obs:
                p0_ships = 0
                p1_ships = 0
                p0_planets = 0
                p1_planets = 0
                
                # orbit wars planets: [id, owner, x, y, radius, ships, prod]
                for p_data in obs["planets"]:
                    owner = p_data[1]
                    ships = p_data[5]
                    if owner == 0:
                        p0_ships += ships
                        p0_planets += 1
                    elif owner == 1:
                        p1_ships += ships
                        p1_planets += 1
                        
                for f_data in obs.get("fleets", []):
                    owner = f_data[1]
                    ships = f_data[6]
                    if owner == 0:
                        p0_ships += ships
                    elif owner == 1:
                        p1_ships += ships
                        
                print(f"  Turn {i:3d} | P0: {p0_planets} planets, {p0_ships} ships | P1: {p1_planets} planets, {p1_ships} ships")

if __name__ == "__main__":
    analyze_replay()
