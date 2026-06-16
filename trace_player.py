import json
with open("replay.json", "r") as f:
    replay = json.load(f)

steps = replay.get("steps", []) if isinstance(replay, dict) else replay

for i, step in enumerate(steps[:50]):
    if isinstance(step, list):
        obs = step[0].get("observation", {})
        
        # Count P0 planets and ships
        p0_planets = 0
        p0_ships = 0
        for p in obs.get("planets", []):
            if p[1] == 0:
                p0_planets += 1
                p0_ships += p[5]
                
        for f in obs.get("fleets", []):
            if f[1] == 0:
                p0_ships += f[6]
                
        # Get actions
        action = step[0].get("action")
        act_str = str(action) if action else "None"
        
        print(f"Step {i:2d}: {p0_planets} planets, {p0_ships} ships | Action: {act_str}")
