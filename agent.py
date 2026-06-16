from world_model import GameState, Planet, Fleet
from planner import BeamSearchPlanner, GreedyPlanner
from ml_planner import MLPlanner
from geometry import line_intersects_circle
from constants import CENTER, SUN_RADIUS

CUSTOM_WEIGHTS = {"alpha": 13.874546103340878, "beta": 0.5383604908917132, "gamma": 1.8718437439968258, "early_prod": 23.20956250372872, "mid_def": 14.009789166567085, "late_agg": 25.993786208225544}

class HistoryTracker:
    def __init__(self):
        self.last_step = -1
        self.opponent_aggression = 0
        self.enemy_launches = []

tracker = HistoryTracker()

def agent(observation, configuration=None):
    """
    Kaggle entry point.
    Wrapped in try/except so no crash ever causes a forfeit.
    """
    global tracker

    try:
        # 1. Parse state
        state = GameState(observation, configuration)
        state.params.update(CUSTOM_WEIGHTS)

        # Track state between turns
        if state.step > tracker.last_step + 1:
            tracker.__init__()  # Reset on new match
        tracker.last_step = state.step
        state.tracker = tracker

        # 2. Plan actions
        if state.step < 16:
            planner = GreedyPlanner(state)
        else:
            # Try to use MLPlanner, fallback to BeamSearch
            try:
                planner = MLPlanner(state)
            except Exception as e:
                planner = BeamSearchPlanner(state, max_time=0.8)
        
        moves = planner.generate_moves()

        # 4. Final safety filter — never send a fleet into the sun
        actions = []
        for m in moves:
            planet_id, angle, ships = m[0], m[1], m[2]

            # Validate: planet must be ours and have enough ships
            if planet_id not in state.planets:
                continue
            p = state.planets[planet_id]
            if p.owner != state.player_id:
                continue
            if ships <= 0 or ships > p.ships:
                ships = min(max(1, ships), p.ships - 1)
                if ships <= 0:
                    continue

            # Validate: fleet path must not hit the sun
            import math
            fx = p.x + math.cos(angle) * (p.radius + 0.1)
            fy = p.y + math.sin(angle) * (p.radius + 0.1)
            far_x = fx + math.cos(angle) * 200
            far_y = fy + math.sin(angle) * 200
            if line_intersects_circle((fx, fy), (far_x, far_y), CENTER, SUN_RADIUS + 0.5):
                continue  # Would fly into the sun — skip

            actions.append([planet_id, angle, ships])

        return actions

    except Exception:
        # NEVER crash — return empty actions instead of forfeiting
        return []
