import json

with open("replay.json", "r") as f:
    replay = json.load(f)

steps = replay.get("steps", []) if isinstance(replay, dict) else replay

player_actions = {}
for i, step in enumerate(steps):
    if isinstance(step, list):
        for p_idx, p_data in enumerate(step):
            act = p_data.get("action")
            if act:
                player_actions[p_idx] = player_actions.get(p_idx, 0) + len(act)

for p, count in player_actions.items():
    print(f"Total P{p} actions: {count}")
