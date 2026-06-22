import math
from world_model import GameState, Planet, Fleet
from planner import BeamSearchPlanner, GreedyPlanner
from geometry import line_intersects_circle
from constants import CENTER, SUN_RADIUS

CUSTOM_WEIGHTS = {"alpha": 13.874546103340878, "beta": 0.5383604908917132, "gamma": 1.8718437439968258, "early_prod": 23.20956250372872, "mid_def": 14.009789166567085, "late_agg": 25.993786208225544}

BEAM_SEARCH_PHASE = 8

class HistoryTracker:
    def __init__(self):
        self.last_step = -1
        self.opponent_aggression = 0
        self.enemy_launches = []

tracker = HistoryTracker()

def safety_filter(moves, state):
    """Validate moves: owned planet, enough ships, no sun collision."""
    actions = []
    for m in moves:
        planet_id, angle, ships = m[0], m[1], m[2]
        if planet_id not in state.planets:
            continue
        p = state.planets[planet_id]
        if p.owner != state.player_id:
            continue
        if ships <= 0 or ships > p.ships:
            ships = min(max(1, ships), p.ships - 1)
            if ships <= 0:
                continue
        fx = p.x + math.cos(angle) * (p.radius + 0.1)
        fy = p.y + math.sin(angle) * (p.radius + 0.1)
        far_x = fx + math.cos(angle) * 200
        far_y = fy + math.sin(angle) * 200
        if line_intersects_circle((fx, fy), (far_x, far_y), CENTER, SUN_RADIUS + 0.5):
            continue
        actions.append([planet_id, angle, ships])
    return actions

def agent(observation, configuration=None):
    try:
        state = GameState(observation, configuration)
        state.params.update(CUSTOM_WEIGHTS)

        if state.step < BEAM_SEARCH_PHASE or len(state.my_planets) < 2:
            planner = GreedyPlanner(state)
            moves = planner.generate_moves()
        else:
            try:
                planner = BeamSearchPlanner(state, max_time=0.8)
                moves = planner.generate_moves()
                if not moves:
                    moves = GreedyPlanner(state).generate_moves()
                return safety_filter(moves, state)
            except Exception:
                pass
            try:
                from mcts_planner import MCTSPlanner as FallbackPlanner
                planner = FallbackPlanner(state, max_time=0.8)
            except Exception:
                try:
                    from ml_planner import MLPlanner as FallbackPlanner
                    planner = FallbackPlanner(state)
                except Exception:
                    planner = BeamSearchPlanner(state, max_time=0.8)
            moves = planner.generate_moves()
            if not moves:
                moves = GreedyPlanner(state).generate_moves()

        return safety_filter(moves, state)

    except Exception:
        return []
