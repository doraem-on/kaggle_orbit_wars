from constants import WEIGHT_PRODUCTION, WEIGHT_TOTAL_SHIPS, WEIGHT_CONTROLLED_PLANETS, MAX_TURNS

def evaluate_state(simulator, player_id: int) -> float:
    """
    Evaluates a simulated game state from the perspective of player_id.
    FFA-aware: compares against the strongest opponent, not the sum of all enemies.
    """
    score = 0.0
    
    my_production = 0
    my_ships = 0
    my_planets = 0
    
    # Track each opponent independently (FFA)
    enemy_stats = {}
    
    for p in simulator.planets.values():
        val = p["production"]
        if p["is_comet"] and p["comet_path"]:
            comet_turns_left = len(p["comet_path"]) - p["comet_path_index"]
            val *= min(1.0, comet_turns_left / 50.0)
            
        if p["owner"] == player_id:
            my_production += val
            my_ships += p["ships"]
            my_planets += 1
        elif p["owner"] != -1:
            eid = p["owner"]
            if eid not in enemy_stats:
                enemy_stats[eid] = {"production": 0, "ships": 0, "planets": 0}
            enemy_stats[eid]["production"] += val
            enemy_stats[eid]["ships"] += p["ships"]
            enemy_stats[eid]["planets"] += 1
            
    for f in simulator.fleets:
        if f["owner"] == player_id:
            my_ships += f["ships"]
        elif f["owner"] != -1:
            eid = f["owner"]
            if eid not in enemy_stats:
                enemy_stats[eid] = {"production": 0, "ships": 0, "planets": 0}
            enemy_stats[eid]["ships"] += f["ships"]
    
    if not enemy_stats:
        # No enemies — we already won
        return 10000.0
    
    # Phase scaling
    turns_left = max(0, MAX_TURNS - simulator.step)
    prod_weight = WEIGHT_PRODUCTION * (turns_left / MAX_TURNS)
    ships_weight = WEIGHT_TOTAL_SHIPS * (1.0 + (MAX_TURNS - turns_left) / MAX_TURNS)
    
    # FFA: We only need to beat the strongest single opponent
    max_enemy_ships = max(es["ships"] for es in enemy_stats.values())
    max_enemy_production = max(es["production"] for es in enemy_stats.values())
    max_enemy_planets = max(es["planets"] for es in enemy_stats.values())
    
    score += (my_production - max_enemy_production) * prod_weight
    score += (my_ships - max_enemy_ships) * ships_weight
    score += (my_planets - max_enemy_planets) * WEIGHT_CONTROLLED_PLANETS
    
    # Bonus for having more planets than ANY single opponent (production snowball)
    if my_planets > max_enemy_planets:
        score += (my_planets - max_enemy_planets) * 10.0
    
    return score
