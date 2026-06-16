from planner import GreedyPlanner, BeamSearchPlanner
from constants import PHASE_END_GAME, PHASE_MID_GAME

def determine_phase(step: int) -> str:
    if step > PHASE_END_GAME:
        return "ENDGAME"
    if step > PHASE_MID_GAME:
        return "MIDGAME"
    return "EXPANSION"

def apply_strategy(state, phase: str):
    if phase == "ENDGAME":
        # In endgame, we use beam search but might focus entirely on capturing to swing ship counts
        planner = BeamSearchPlanner(state, max_time=0.8)
        return planner.generate_moves()
    elif phase == "MIDGAME":
        planner = BeamSearchPlanner(state, max_time=0.8)
        return planner.generate_moves()
    else:
        # Early expansion: Greedy is fast and good enough
        planner = GreedyPlanner(state)
        return planner.generate_moves()
