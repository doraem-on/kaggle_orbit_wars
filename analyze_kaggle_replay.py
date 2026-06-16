import json
import sys

def run(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    
    # Kaggle replays usually have "info" and "steps"
    info = data.get("info", {})
    players = info.get("TeamNames", [])
    print(f"Match Info: {info}")
    
    lalit_id = -1
    for i, name in enumerate(players):
        if "Lalit" in name:
            lalit_id = i
            break
            
    if lalit_id == -1:
        print("Lalit not found in players:", players)
        # We'll just trace player 0 or guess
        # In a 4-player game, teams might be under a different key
        pass
        
    steps = data.get("steps", [])
    if not steps:
        print("No steps found")
        return
        
    print(f"Total steps: {len(steps)}")
    
    # Try to find Lalit's ID from step 0 observation if TeamNames wasn't accurate
    if lalit_id == -1:
        # In some formats, players don't have explicit names in replay JSON easily accessible.
        # Let's just track all players.
        num_players = len(steps[0])
        print(f"Tracking {num_players} players")
        
    for i, step in enumerate(steps):
        # Kaggle step is a list of player dicts
        if not isinstance(step, list): continue
        
        print(f"--- Turn {i} ---")
        for p_idx, p_data in enumerate(step):
            status = p_data.get("status")
            action = p_data.get("action")
            reward = p_data.get("reward")
            obs = p_data.get("observation", {})
            
            # Count ships/planets if we can
            planets = obs.get("planets", [])
            my_planets = 0
            my_ships = 0
            for p in planets:
                if p[1] == p_idx:
                    my_planets += 1
                    my_ships += p[5]
            
            fleets = obs.get("fleets", [])
            for f in fleets:
                if f[1] == p_idx:
                    my_ships += f[6]
            
            action_str = str(action) if action else "[]"
            # Only print if something interesting happened or for our presumed user
            if my_planets > 0 or my_ships > 0 or action or status != "ACTIVE":
                print(f"  P{p_idx} [{status}] | Reward: {reward} | Planets: {my_planets}, Ships: {my_ships} | Action: {action_str}")

if __name__ == "__main__":
    run(sys.argv[1])
