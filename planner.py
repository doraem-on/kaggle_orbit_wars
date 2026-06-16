import math
import time
import itertools
from typing import List, Tuple
from geometry import line_intersects_circle, angle_between, get_orbit_intercept, get_path_intercept
from constants import CENTER, SUN_RADIUS, get_fleet_speed
from simulator import Simulator
from evaluator import evaluate_state

class ActionGenerator:
    def __init__(self, state):
        self.state = state
        self.arrivals = {p.id: {} for p in self.state.planets.values()}
        self.incoming_enemy = {p.id: 0 for p in self.state.planets.values()}
        
        for f in self.state.fleets:
            target_id = self.get_fleet_target(f)
            if target_id is not None:
                p = self.state.planets[target_id]
                dist = math.hypot(p.x - f.x, p.y - f.y)
                turns = int(math.ceil(max(0, dist - p.radius) / f.speed))
                
                if f.owner != self.state.player_id:
                    self.incoming_enemy[target_id] += f.ships
                    
                if turns not in self.arrivals[target_id]:
                    self.arrivals[target_id][turns] = {}
                self.arrivals[target_id][turns][f.owner] = self.arrivals[target_id][turns].get(f.owner, 0) + f.ships
                
        # Sort arrivals
        for p_id in self.arrivals:
            self.arrivals[p_id] = sorted(list(self.arrivals[p_id].items()), key=lambda x: x[0])
            
    def get_fleet_target(self, fleet):
        fx, fy = fleet.pos
        nx = fx + math.cos(fleet.angle) * 200
        ny = fy + math.sin(fleet.angle) * 200
        best_p = None
        best_dist = 9999
        for p in self.state.planets.values():
            if line_intersects_circle((fx, fy), (nx, ny), p.pos, p.radius):
                dist = math.hypot(p.x - fx, p.y - fy)
                if dist < best_dist:
                    best_dist = dist
                    best_p = p.id
        return best_p

    def forecast_planet(self, target_id, turns_ahead):
        p = self.state.planets[target_id]
        owner = p.owner
        ships = p.ships
        
        current_turn = 0
        
        for turn, forces in self.arrivals[target_id]:
            if turn > turns_ahead:
                break
                
            if owner != -1:
                ships += p.production * (turn - current_turn)
            current_turn = turn
            
            # Combat
            forces_copy = dict(forces)
            forces_copy[owner] = forces_copy.get(owner, 0) + ships
            
            sorted_forces = sorted(forces_copy.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_forces) == 1:
                owner = sorted_forces[0][0]
                ships = sorted_forces[0][1]
            else:
                top_owner, top_ships = sorted_forces[0]
                sec_owner, sec_ships = sorted_forces[1]
                survivors = top_ships - sec_ships
                if survivors == 0:
                    owner = -1
                    ships = 0
                else:
                    owner = top_owner
                    ships = survivors
                    
        if owner != -1:
            ships += p.production * (turns_ahead - current_turn)
            
        return owner, ships

    def get_candidate_targets(self, source_planet, available_ships, max_targets=3):
        candidates = []
        source_reserve = max(self.state.params["reserve_ships_min"], self.incoming_enemy.get(source_planet.id, 0))

        for target in self.state.planets.values():
            if target.id == source_planet.id:
                continue

            required_ships_base = target.ships
            speed = get_fleet_speed(max(1, required_ships_base + 5))
            
            if target.is_comet and target.comet_path:
                angle, turns = get_path_intercept(source_planet.pos, speed, target.comet_path, target.comet_path_index, target.radius)
            elif target.is_orbiting:
                angle, turns = get_orbit_intercept(source_planet.pos, speed, target.x, target.y, target.angular_velocity, target.radius)
            else:
                dist = math.hypot(target.x - source_planet.pos[0], target.y - source_planet.pos[1])
                dist_travel = max(0, dist - target.radius)
                turns = int(math.ceil(dist_travel / speed)) if speed > 0 else 9999
                angle = math.atan2(target.y - source_planet.pos[1], target.x - source_planet.pos[0])
                
            if turns > 300:
                continue
                
            future_pos = target.predict_pos(turns)
            if line_intersects_circle(source_planet.pos, future_pos, CENTER, SUN_RADIUS + 0.5):
                continue
                
            is_mine = (target.owner == self.state.player_id)
            is_enemy = (target.owner != self.state.player_id and target.owner != -1)
            
            # Robust needed calculation: count all enemy fleets currently flying towards it
            needed = target.ships + self.incoming_enemy[target.id]
            if is_enemy:
                needed += target.production * turns
            elif is_mine:
                needed -= target.production * turns
                
            needed += self.state.params["defense_buffer_ships"]
            
            if is_mine:
                # If we already have more incoming allied ships than the enemy, we don't need to send more
                if self.incoming_enemy[target.id] > (target.ships + target.production * turns): # Simplified check
                    score = 1000 + target.production * self.state.params["defense_score_multiplier"] - turns
                    needed = max(1, self.incoming_enemy[target.id] - target.ships - (target.production * turns))
                else:
                    continue
            else:
                score = (target.production * self.state.params["attack_score_multiplier"]) - turns
                
            if available_ships - source_reserve > needed:
                candidates.append({
                    "target": target.id,
                    "angle": angle,
                    "ships": int(needed),
                    "score": score
                })
                
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:max_targets]

class GreedyPlanner:
    def __init__(self, game_state):
        self.state = game_state
        self.generator = ActionGenerator(game_state)
        
    def generate_moves(self) -> List[Tuple[int, float, int]]:
        moves = []
        sent_to_target = {}
        use_dedup = self.state.params.get("deduplicate_targets", True)
        
        # Sort planets by how many ships they have, so biggest planets act first
        # Alternatively, sort by distance to enemy. For now, biggest ships first.
        sorted_planets = sorted(self.state.my_planets, key=lambda p: p.ships, reverse=True)
        
        for source in sorted_planets:
            available_ships = source.ships
            
            max_t = self.state.params.get("max_targets", 5)
            candidates = self.generator.get_candidate_targets(source, available_ships, max_targets=max_t)
            for cand in candidates:
                target_id = cand["target"]
                needed = int(cand["ships"])
                
                if use_dedup:
                    already_sent = sent_to_target.get(target_id, 0)
                    needed -= already_sent
                    if needed <= 0:
                        continue
                
                source_reserve = max(self.state.params["reserve_ships_min"], self.generator.incoming_enemy.get(source.id, 0))
                
                if available_ships - source_reserve > needed:
                    moves.append((source.id, cand["angle"], needed))
                    available_ships -= needed
                    
                    if use_dedup:
                        sent_to_target[target_id] = sent_to_target.get(target_id, 0) + needed
        return moves

class BeamSearchPlanner:
    def __init__(self, game_state, max_time=0.8):
        self.state = game_state
        self.generator = ActionGenerator(game_state)
        self.max_time = max_time
        
    def generate_moves(self) -> List[Tuple[int, float, int]]:
        start_time = time.time()
        
        # 1. Gather candidates for each planet
        planet_moves = []
        for source in self.state.my_planets:
            cands = self.generator.get_candidate_targets(source, source.ships, max_targets=2)
            valid_moves = [None] # Null action
            for c in cands:
                valid_moves.append((source.id, c["angle"], int(c["ships"])))
                
                # Option to dump all remaining ships (Endgame Swarm)
                source_reserve = max(self.state.params["reserve_ships_min"], self.generator.incoming_enemy.get(source.id, 0))
                dump_amount = source.ships - source_reserve
                if dump_amount > int(c["ships"]) + 10: # Only if it's significantly more
                    valid_moves.append((source.id, c["angle"], dump_amount))
                    
            if len(valid_moves) > 1:
                planet_moves.append(valid_moves)
                
        if not planet_moves:
            return []
            
        # 2. Generate combinations (Cartesian product)
        # To avoid exploding, limit number of combinations
        all_combos = list(itertools.product(*planet_moves))
        if len(all_combos) > 200:
            # Sort individual planets by their best move score to prioritize
            # But for simplicity, just truncate or use greedy fallback
            pass
            
        best_combo = None
        best_score = -999999
        
        for combo in all_combos[:200]: # Cap at 200 combinations to ensure we don't timeout
            if time.time() - start_time > self.max_time:
                break
                
            # Filter out Nones
            actual_moves = [m for m in combo if m is not None]
            
            # Simulate
            sim = Simulator(self.state)
            for m in actual_moves:
                sim.add_launch(m[0], m[1], m[2])
                
            sim.simulate_ahead(25) # Lookahead 25 turns
            score = evaluate_state(sim, self.state.player_id)
            
            # Penalize slightly for launching ships to break ties and save ships when useless
            score -= len(actual_moves) * 0.1
            
            if score > best_score:
                best_score = score
                best_combo = actual_moves
                
        return best_combo if best_combo else []
