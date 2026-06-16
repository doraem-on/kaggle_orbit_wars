from world_model import GameState
from strategy import determine_phase, apply_strategy

def agent(observation, configuration=None):
    """
    Kaggle entry point.
    """
    # 1. Parse state
    state = GameState(observation, configuration)
    
    # 2. Determine strategic phase
    phase = determine_phase(state.step)
    
    # 3. Plan actions
    moves = apply_strategy(state, phase)
    
    # Format for Kaggle: list of [from_planet_id, direction_angle, num_ships]
    actions = []
    for m in moves:
        actions.append([m[0], m[1], m[2]])
        
    return actions
