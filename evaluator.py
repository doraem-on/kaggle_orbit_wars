from constants import WEIGHT_PRODUCTION, WEIGHT_TOTAL_SHIPS, WEIGHT_CONTROLLED_PLANETS, MAX_TURNS

def evaluate_state(simulator, player_id: int) -> float:
    """
    Evaluates a simulated game state from the perspective of player_id.
    """
    score = 0.0
    
    my_production = 0
    enemy_production = 0
    my_ships = 0
    enemy_ships = 0
    my_planets = 0
    enemy_planets = 0
    
    # Phase scaling: as game nears end, production matters less, total ships matter more
    turns_left = max(0, MAX_TURNS - simulator.step)
    prod_weight = WEIGHT_PRODUCTION * (turns_left / MAX_TURNS)
    ships_weight = WEIGHT_TOTAL_SHIPS * (1.0 + (MAX_TURNS - turns_left) / MAX_TURNS)
    
    for p in simulator.planets.values():
        val = p["production"]
        # Discount comet production based on how long it has left
        if p["is_comet"] and p["comet_path"]:
            comet_turns_left = len(p["comet_path"]) - p["comet_path_index"]
            val *= min(1.0, comet_turns_left / 50.0)
            
        if p["owner"] == player_id:
            my_production += val
            my_ships += p["ships"]
            my_planets += 1
        elif p["owner"] != -1:
            enemy_production += val
            enemy_ships += p["ships"]
            enemy_planets += 1
            
    for f in simulator.fleets:
        if f["owner"] == player_id:
            my_ships += f["ships"]
        elif f["owner"] != -1:
            enemy_ships += f["ships"]

    score += (my_production - enemy_production) * prod_weight
    score += (my_ships - enemy_ships) * ships_weight
    score += (my_planets - enemy_planets) * WEIGHT_CONTROLLED_PLANETS
    
    return score
