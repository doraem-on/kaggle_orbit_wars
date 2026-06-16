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

obs = MockObs(step=100, planets=[
    [0, 0, 25, 80, 5, 100, 5], [1, 1, 75, 80, 5, 50, 5], [2, -1, 50, 85, 3, 10, 2],
])

from world_model import GameState
from planner import BeamSearchPlanner
from simulator import Simulator
from evaluator import evaluate_state

state = GameState(obs, MockConfig())
planner = BeamSearchPlanner(state)
planner.max_time = 10.0

print("Planet candidates:", planner.generator.get_candidate_targets(state.my_planets[0], 100))

beam = planner.generate_moves()
print("Final Beam:", beam)

# trace evaluator
target_neutral = planner.generator.get_candidate_targets(state.my_planets[0], 100)
angle = target_neutral[0]['angle'] if target_neutral else 0.0
ships = target_neutral[0]['ships'] if target_neutral else 15

joint_actions = [[], [(0, angle, ships)]] 
for actual_moves in joint_actions:
    sim = Simulator(state)
    for m in actual_moves:
        sim.add_launch(m[0], m[1], m[2])
    sim.simulate_ahead(20)
    score = evaluate_state(sim, state.player_id, state.max_turns)
    print("Action", actual_moves, "Score:", score)
