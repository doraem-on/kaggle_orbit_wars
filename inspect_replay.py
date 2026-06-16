import json
with open("replay.json", "r") as f:
    replay = json.load(f)

steps = replay.get("steps", []) if isinstance(replay, dict) else replay
if steps and len(steps) > 5:
    print(json.dumps(steps[5], indent=2)[:1000])
