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
        self.incoming_allied = {p.id: 0 for p in self.state.planets.values()}
        
        for f in self.state.fleets:
            target_id = self.get_fleet_target(f)
            if target_id is not None:
                p = self.state.planets[target_id]
                dist = math.hypot(p.x - f.x, p.y - f.y)
                turns = int(math.ceil(max(0, dist - p.radius) / f.speed))
                
                if f.owner != self.state.player_id:
                    self.incoming_enemy[target_id] += f.ships
                else:
                    self.incoming_allied[target_id] += f.ships
                    
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
        max_sendable = available_ships - source_reserve

        # FFA: Track strongest opponent for leader-targeting
        enemy_prod = {}
        for p in self.state.planets.values():
            if p.owner not in (-1, self.state.player_id):
                enemy_prod[p.owner] = enemy_prod.get(p.owner, 0) + p.production
        leader_id = max(enemy_prod, key=enemy_prod.get) if enemy_prod else None

        for target in self.state.planets.values():
            if target.id == source_planet.id:
                continue

            # Estimate ships we'd actually send (use a reasonable guess for speed calc)
            est_send = min(max(1, int(target.ships * 1.5)), max_sendable)
            speed = get_fleet_speed(est_send)
            
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
            
            # Account for all forces: garrison, production, incoming fleets (both sides)
            garrison_upon_arrival = target.ships + (target.production * turns if target.owner != -1 else 0)
            enemy_arriving = self.incoming_enemy.get(target.id, 0)
            allied_arriving = self.incoming_allied.get(target.id, 0)
            
            if is_mine:
                # Proactive defense: send ships if the planet would be lost without reinforcement
                net_enemy_after_defense = enemy_arriving - allied_arriving
                needed = max(0, net_enemy_after_defense - garrison_upon_arrival) + self.state.params["defense_buffer_ships"]
                if needed > 0:
                    score = 1500 + target.production * self.state.params["defense_score_multiplier"] - turns
                else:
                    # Planet is safe with existing allied fleets — no need to send more
                    continue
            elif is_enemy:
                # Attack: we need to overcome garrison + production + enemy reinforcements
                needed = garrison_upon_arrival + max(0, enemy_arriving - allied_arriving) + self.state.params["defense_buffer_ships"]
                # FFA bonus: attacking the leader is worth more
                leader_bonus = 200 if target.owner == leader_id else 0
                score = (target.production * self.state.params["attack_score_multiplier"]) - turns + leader_bonus
            else:
                # Neutral: just need to beat garrison (production only helps defender if it has an owner)
                needed = garrison_upon_arrival + self.state.params["defense_buffer_ships"]
                score = (target.production * self.state.params["attack_score_multiplier"]) - turns
                
            if max_sendable > needed:
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
        
        # 1. Gather candidates for each planet, tracking scores for ranking
        planet_moves = []
        planet_move_scores = []  # parallel list: scores for each move option
        
        for source in self.state.my_planets:
            source_reserve = max(self.state.params["reserve_ships_min"], self.generator.incoming_enemy.get(source.id, 0))
            cands = self.generator.get_candidate_targets(source, source.ships, max_targets=3)
            valid_moves = [None]
            move_scores = [0.0]  # null action = score 0
            for c in cands:
                valid_moves.append((source.id, c["angle"], int(c["ships"])))
                move_scores.append(c["score"])
                
                dump_amount = source.ships - source_reserve
                if dump_amount > int(c["ships"]) + 10:
                    valid_moves.append((source.id, c["angle"], dump_amount))
                    move_scores.append(c["score"] + 5)  # slightly favor dumping in endgame
                    
            if len(valid_moves) > 1:
                planet_moves.append(valid_moves)
                planet_move_scores.append(move_scores)
                
        if not planet_moves:
            return []
            
        # 2. Generate and prioritize combinations
        lookahead = 25
        max_combos = 200
        all_combos = list(itertools.product(*planet_moves))
        
        if len(all_combos) > max_combos:
            # Score each combo by sum of its move scores
            combo_scores = []
            for combo in all_combos:
                total = 0.0
                for i, m in enumerate(combo):
                    if m is not None:
                        idx = planet_moves[i].index(m)
                        total += planet_move_scores[i][idx]
                combo_scores.append((total, combo))
            combo_scores.sort(key=lambda x: x[0], reverse=True)
            all_combos = [c for _, c in combo_scores[:max_combos]]
            
        best_combo = None
        best_score = -999999
        
        for combo in all_combos:
            if time.time() - start_time > self.max_time:
                break
                
            actual_moves = [m for m in combo if m is not None]
            
            sim = Simulator(self.state)
            for m in actual_moves:
                sim.add_launch(m[0], m[1], m[2])
                
            sim.simulate_ahead(lookahead)
            score = evaluate_state(sim, self.state.player_id)
            score -= len(actual_moves) * 0.1
            
            if score > best_score:
                best_score = score
                best_combo = actual_moves
                
        return best_combo if best_combo else []
