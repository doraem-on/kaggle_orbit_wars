import math

# Board and Physics
BOARD_SIZE = 100.0
CENTER = (50.0, 50.0)
SUN_RADIUS = 10.0
ROTATION_RADIUS_LIMIT = 50.0  # (orbital_radius + planet_radius < 50) means it rotates

# Gameplay
MAX_TURNS = 500
MAX_FLEET_SPEED = 6.0
COMET_SPEED = 4.0

# Strategic / Evaluation Weights
WEIGHT_PRODUCTION = 3.0
WEIGHT_TOTAL_SHIPS = 1.0
WEIGHT_CONTROLLED_PLANETS = 2.0

# Phases
PHASE_EARLY_GAME = 100
PHASE_MID_GAME = 350
PHASE_END_GAME = 450

def get_fleet_speed(ships: int) -> float:
    """Calculate fleet speed based on ship count."""
    if ships <= 1:
        return 1.0
    
    # speed = 1.0 + (maxSpeed - 1.0) * (log(ships) / log(1000)) ^ 1.5
    # Cap log(ships) to log(1000) for max speed scaling, though theoretically ships could be >1000
    ratio = math.log(ships) / math.log(1000.0)
    # The game doesn't strictly cap speed at ships=1000 in the formula but usually approaches 6.0.
    # Let's cap ratio at 1.0 or let it exceed if ships > 1000? 
    # Usually maxSpeed is the cap, but if ships > 1000, speed could exceed 6.0?
    # Let's bound it to avoid math domain errors if ratio is negative (not possible since ships >= 1)
    
    if ratio < 0:
        ratio = 0
    return 1.0 + (MAX_FLEET_SPEED - 1.0) * (ratio ** 1.5)
