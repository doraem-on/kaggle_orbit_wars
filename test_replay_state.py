import json
from world_model import GameState
from planner import BeamSearchPlanner

class MockConfig:
    pass

with open("replay.json", "r") as f:
    replay = json.load(f)

steps = replay.get("steps", []) if isinstance(replay, dict) else replay
step0 = steps[0]
obs_data = step0[0].get("observation", {}) if isinstance(step0, list) else step0

class DictObj:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)
    def get(self, k, default=None):
        return getattr(self, k, default)

obs = DictObj(obs_data)
state = GameState(obs, MockConfig())
planner = BeamSearchPlanner(state)

print("Player ID:", state.player_id)
print("My planets:", [(p.id, p.ships) for p in state.my_planets])
print("Neutral planets:", len(state.neutral_planets))

for p in state.my_planets:
    cands = planner.generator.get_candidate_targets(p, p.ships)
    print(f"Candidates for planet {p.id}: {cands}")

beam = planner.generate_moves()
print(f"Generated moves: {beam}")

from agent import agent
actual_actions = agent(obs_data, MockConfig())
print(f"Agent final output: {actual_actions}")
