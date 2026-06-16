import json
from world_model import GameState
from simulator import Simulator
from tune import MockObs, MockConfig

# Import OLD evaluator
import sys
sys.path.insert(0, "./old_bot")
from old_bot.evaluator import evaluate_state as old_evaluate_state
sys.path.pop(0)

# Import NEW evaluator
from evaluator import evaluate_state as new_evaluate_state

def test_phase_bug():
    # Simulate a standard turn 1 state in a 1v1 match
    # 2 players, low production ratio for player 0
    planets = [
        [0, 0, 10, 50, 5, 100, 5],
        [1, 1, 90, 50, 5, 100, 5],
        # Neutrals
        [2, -1, 50, 20, 3, 15, 3],
        [3, -1, 50, 80, 3, 15, 3]
    ]
    
    config = MockConfig()
    config.episodeSteps = 300
    
    obs = MockObs(step=0, player=0, planets=planets, fleets=[])
    state = GameState(obs, config)
    sim = Simulator(state)
    sim.fleets = []
    
    params = {
        "early_prod": 25.0,
        "mid_def": 15.0,
        "late_agg": 25.0
    }
    
    # We will hack the evaluators slightly by just passing params
    # and reading what weight it chose for production.
    # In EARLY game, weight is 25.0
    # In MID game, weight is 15.0
    # In LATE game, weight is 5.0
    
    print("Testing Turn 1 (1v1 Match)")
    
    # OLD BOT EVALUATOR
    try:
        old_evaluate_state(sim, 0, 300, params)
    except Exception as e:
        print("Old Eval failed", e)
        
    # NEW BOT EVALUATOR
    try:
        new_evaluate_state(sim, 0, 300, params)
    except Exception as e:
        print("New Eval failed", e)
        
    print("Done (Modify evaluators to print phase to see output)")

if __name__ == "__main__":
    test_phase_bug()
