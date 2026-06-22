from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple
from typing import List, Dict, Tuple, Optional
from typing import List, Tuple
from typing import Tuple
import itertools
import math
import time


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



Point = Tuple[float, float]

def distance(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def angle_between(p1: Point, p2: Point) -> float:
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

def line_intersects_circle(start: Point, end: Point, center: Point, radius: float) -> bool:
    """
    Check if a line segment from `start` to `end` intersects a circle at `center` with `radius`.
    Uses continuous collision detection (checks the whole segment, not just endpoints).
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    fx = start[0] - center[0]
    fy = start[1] - center[1]
    
    a = dx*dx + dy*dy
    b = fx*dx + fy*dy
    c = fx*fx + fy*fy - radius*radius
    
    if a == 0:
        return c <= 0
    
    t = -b / a
    t = max(0.0, min(1.0, t))
    
    return (a * t * t + 2 * b * t + c) <= 0

def predict_planet_pos(x: float, y: float, turns: int, angular_velocity: float, center: Point = (50.0, 50.0)) -> Point:
    """Predict where an orbiting planet will be after `turns`."""
    if angular_velocity == 0:
        return (x, y)
    
    dx = x - center[0]
    dy = y - center[1]
    
    current_angle = math.atan2(dy, dx)
    orbital_radius = math.hypot(dx, dy)
    
    new_angle = current_angle + (angular_velocity * turns)
    
    new_x = center[0] + orbital_radius * math.cos(new_angle)
    new_y = center[1] + orbital_radius * math.sin(new_angle)
    
    return (new_x, new_y)

def move_point_towards(start: Point, angle: float, dist: float) -> Point:
    """Returns a new point after moving `dist` distance in `angle` direction."""
    return (start[0] + math.cos(angle) * dist, start[1] + math.sin(angle) * dist)

def get_orbit_intercept(start: Point, speed: float, target_x: float, target_y: float, angular_velocity: float, target_radius: float, max_turns: int = 500, center: Point = (50.0, 50.0)) -> Tuple[float, int]:
    """Iteratively calculate exact intercept angle and arrival time for an orbiting planet."""
    if angular_velocity == 0:
        dist = math.hypot(target_x - start[0], target_y - start[1])
        dist_to_travel = max(0, dist - target_radius)
        turns = int(math.ceil(dist_to_travel / speed)) if speed > 0 else 9999
        angle = math.atan2(target_y - start[1], target_x - start[0])
        return angle, turns
        
    dx = target_x - center[0]
    dy = target_y - center[1]
    current_angle = math.atan2(dy, dx)
    orbital_radius = math.hypot(dx, dy)
    
    t = math.hypot(target_x - start[0], target_y - start[1]) / speed
    for _ in range(15):
        new_angle = current_angle + (angular_velocity * t)
        nx = center[0] + orbital_radius * math.cos(new_angle)
        ny = center[1] + orbital_radius * math.sin(new_angle)
        dist = math.hypot(nx - start[0], ny - start[1])
        t_new = max(0, dist - target_radius) / speed
        if abs(t - t_new) < 0.1:
            t = t_new
            break
        t = t_new
    
    turns = int(math.ceil(t))
    final_angle = current_angle + (angular_velocity * turns)
    fx = center[0] + orbital_radius * math.cos(final_angle)
    fy = center[1] + orbital_radius * math.sin(final_angle)
    
    launch_angle = math.atan2(fy - start[1], fx - start[0])
    return launch_angle, turns

def get_path_intercept(start: Point, speed: float, path: list, current_index: int, target_radius: float) -> Tuple[float, int]:
    """Calculate intercept for a comet on a predefined path."""
    for t in range(len(path) - current_index):
        target_pos = path[current_index + t]
        dist = math.hypot(target_pos[0] - start[0], target_pos[1] - start[1])
        dist_to_travel = max(0, dist - target_radius)
        if dist_to_travel <= t * speed:
            launch_angle = math.atan2(target_pos[1] - start[1], target_pos[0] - start[0])
            return launch_angle, t
    # Fallback if unreachable
    return 0.0, 9999



@dataclass
class Planet:
    id: int
    owner: int
    x: float
    y: float
    radius: float
    ships: int
    production: int
    is_comet: bool = False
    
    # Path/Orbit data
    angular_velocity: float = 0.0
    comet_path: Optional[List[Tuple[float, float]]] = None
    comet_path_index: int = 0
    
    @property
    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)
        
    @property
    def orbital_radius(self) -> float:
        return distance(self.pos, CENTER)
        
    @property
    def is_orbiting(self) -> bool:
        return not self.is_comet and (self.orbital_radius + self.radius < ROTATION_RADIUS_LIMIT)
        
    def predict_pos(self, turns_ahead: int) -> Tuple[float, float]:
        if self.is_comet and self.comet_path:
            idx = min(self.comet_path_index + turns_ahead, len(self.comet_path) - 1)
            return self.comet_path[idx]
        elif self.is_orbiting:
            return predict_planet_pos(self.x, self.y, turns_ahead, self.angular_velocity, CENTER)
        return self.pos

@dataclass
class Fleet:
    id: int
    owner: int
    x: float
    y: float
    angle: float
    from_planet_id: int
    ships: int
    
    @property
    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)
        
    @property
    def speed(self) -> float:
        return get_fleet_speed(self.ships)

class GameState:
    def __init__(self, obs, config):
        self.step = getattr(obs, "step", obs.get("step", 0) if hasattr(obs, "get") else 0)
        self.player_id = getattr(obs, "player", obs.get("player", 0) if hasattr(obs, "get") else 0)
        self.angular_velocity = getattr(obs, "angular_velocity", obs.get("angular_velocity", 0.0) if hasattr(obs, "get") else 0.0)
        self.config = config if config is not None else {}
        
        # Load configurable parameters (falling back to constants.py defaults or hardcoded defaults)
        # Note: If config is a Kaggle configuration object, it acts like a dict
        self.params = {
            "defense_score_multiplier": getattr(self.config, "get", lambda k,d: d)("defense_score_multiplier", 50.0),
            "attack_score_multiplier": getattr(self.config, "get", lambda k,d: d)("attack_score_multiplier", 15.0),
            "defense_buffer_ships": getattr(self.config, "get", lambda k,d: d)("defense_buffer_ships", 2),
            "reserve_ships_min": getattr(self.config, "get", lambda k,d: d)("reserve_ships_min", 5),
            "deduplicate_targets": getattr(self.config, "get", lambda k,d: d)("deduplicate_targets", True),
            "max_targets": getattr(self.config, "get", lambda k,d: d)("max_targets", 5)
        }
        
        self.planets: Dict[int, Planet] = {}
        self.fleets: List[Fleet] = []
        
        self._parse_obs(obs)
        
    def _parse_obs(self, obs):
        comet_ids = set(getattr(obs, "comet_planet_ids", obs.get("comet_planet_ids", []) if hasattr(obs, "get") else []))
        
        comet_paths = {}
        comets_list = getattr(obs, "comets", obs.get("comets", []) if hasattr(obs, "get") else [])
        for comet_group in comets_list:
            paths = comet_group.get("paths", [])
            path_index = comet_group.get("path_index", 0)
            p_ids = comet_group.get("planet_ids", [])
            for i, p_id in enumerate(p_ids):
                if i < len(paths):
                    comet_paths[p_id] = {
                        "path": paths[i],
                        "index": path_index
                    }
        
        planets_data = getattr(obs, "planets", obs.get("planets", []) if hasattr(obs, "get") else [])
        for p_data in planets_data:
            p_id, owner, x, y, radius, ships, production = p_data
            is_comet = p_id in comet_ids
            
            p = Planet(
                id=p_id, owner=owner, x=x, y=y, radius=radius,
                ships=ships, production=production, is_comet=is_comet,
                angular_velocity=self.angular_velocity
            )
            
            if is_comet and p_id in comet_paths:
                p.comet_path = comet_paths[p_id]["path"]
                p.comet_path_index = comet_paths[p_id]["index"]
                
            self.planets[p_id] = p
            
        fleets_data = getattr(obs, "fleets", obs.get("fleets", []) if hasattr(obs, "get") else [])
        for f_data in fleets_data:
            f_id, owner, x, y, angle, from_p_id, ships = f_data
            self.fleets.append(Fleet(
                id=f_id, owner=owner, x=x, y=y, angle=angle,
                from_planet_id=from_p_id, ships=ships
            ))
            
    @property
    def my_planets(self) -> List[Planet]:
        return [p for p in self.planets.values() if p.owner == self.player_id]
        
    @property
    def enemy_planets(self) -> List[Planet]:
        return [p for p in self.planets.values() if p.owner not in (self.player_id, -1)]
        
    @property
    def neutral_planets(self) -> List[Planet]:
        return [p for p in self.planets.values() if p.owner == -1]



class Simulator:
    """
    Step-by-step simulator for forward prediction.
    """
    def __init__(self, game_state):
        self.step = game_state.step
        
        self.planets = {}
        for p in game_state.planets.values():
            self.planets[p.id] = {
                "id": p.id,
                "owner": p.owner,
                "x": p.x,
                "y": p.y,
                "radius": p.radius,
                "ships": p.ships,
                "production": p.production,
                "is_comet": p.is_comet,
                "angular_velocity": p.angular_velocity,
                "comet_path": p.comet_path,
                "comet_path_index": p.comet_path_index,
                "is_orbiting": p.is_orbiting
            }
            
        self.fleets = []
        for f in game_state.fleets:
            self.fleets.append({
                "id": f.id,
                "owner": f.owner,
                "x": f.x,
                "y": f.y,
                "angle": f.angle,
                "ships": f.ships,
                "speed": f.speed
            })
            
        self.next_fleet_id = max([f.id for f in game_state.fleets] + [0]) + 1
        
    def add_launch(self, planet_id: int, angle: float, ships: int):
        p = self.planets[planet_id]
        if p["ships"] >= ships:
            p["ships"] -= ships
            # Spawn just outside radius
            fx = p["x"] + math.cos(angle) * (p["radius"] + 0.1)
            fy = p["y"] + math.sin(angle) * (p["radius"] + 0.1)
            self.fleets.append({
                "id": self.next_fleet_id,
                "owner": p["owner"],
                "x": fx,
                "y": fy,
                "angle": angle,
                "ships": ships,
                "speed": get_fleet_speed(ships)
            })
            self.next_fleet_id += 1

    def clone(self):
        # Extremely fast shallow/deep copy for MCTS
        new_sim = Simulator.__new__(Simulator)
        new_sim.step = self.step
        new_sim.next_fleet_id = self.next_fleet_id
        
        # Dict of dicts -> fast copy
        new_sim.planets = {}
        for p_id, p in self.planets.items():
            new_sim.planets[p_id] = p.copy()
            
        # List of dicts -> fast copy
        new_sim.fleets = [f.copy() for f in self.fleets]
        
        return new_sim

    def simulate_ahead(self, turns: int):
        for _ in range(turns):
            self.step += 1
            self._step()
            
    def _step(self):
        # 1. Comet expiration
        expired_comets = []
        for p_id, p in self.planets.items():
            if p["is_comet"]:
                # If path is complete, it expires
                if p["comet_path"] and p["comet_path_index"] >= len(p["comet_path"]) - 1:
                    expired_comets.append(p_id)
        for p_id in expired_comets:
            del self.planets[p_id]
            
        # 2. Comet spawning (ignored for future prediction since we don't know where)
        # 3. Fleet launch (done manually via add_launch)
        # 4. Production
        for p in self.planets.values():
            if p["owner"] != -1:
                p["ships"] += p["production"]
                
        # 5. Fleet movement
        queued_combats = defaultdict(lambda: defaultdict(int)) # p_id -> owner -> ships
        active_fleets = []
        
        for f in self.fleets:
            nx = f["x"] + math.cos(f["angle"]) * f["speed"]
            ny = f["y"] + math.sin(f["angle"]) * f["speed"]
            
            # Out of bounds
            if not (0 <= nx <= 100 and 0 <= ny <= 100):
                continue
                
            # Sun collision
            if line_intersects_circle((f["x"], f["y"]), (nx, ny), CENTER, SUN_RADIUS):
                continue
                
            # Planet collision
            hit_planet = None
            for p_id, p in self.planets.items():
                if line_intersects_circle((f["x"], f["y"]), (nx, ny), (p["x"], p["y"]), p["radius"]):
                    hit_planet = p_id
                    break
                    
            if hit_planet is not None:
                queued_combats[hit_planet][f["owner"]] += f["ships"]
            else:
                f["x"] = nx
                f["y"] = ny
                active_fleets.append(f)
                
        self.fleets = active_fleets
        
        # 6. Planet rotation & comet movement
        swept_fleets = set()
        for p_id, p in self.planets.items():
            old_pos = (p["x"], p["y"])
            moved = False
            if p["is_comet"] and p["comet_path"]:
                p["comet_path_index"] = min(p["comet_path_index"] + 1, len(p["comet_path"]) - 1)
                new_pos = p["comet_path"][p["comet_path_index"]]
                p["x"], p["y"] = new_pos
                moved = True
            elif p["is_orbiting"] and p["angular_velocity"] != 0:
                new_pos = predict_planet_pos(p["x"], p["y"], 1, p["angular_velocity"], CENTER)
                p["x"], p["y"] = new_pos
                moved = True
                
            if moved:
                # Check for swept fleets
                for i, f in enumerate(self.fleets):
                    if i in swept_fleets:
                        continue
                    if line_intersects_circle(old_pos, (p["x"], p["y"]), (f["x"], f["y"]), p["radius"]):
                        queued_combats[p_id][f["owner"]] += f["ships"]
                        swept_fleets.add(i)
                        
        if swept_fleets:
            self.fleets = [f for i, f in enumerate(self.fleets) if i not in swept_fleets]
            
        # 7. Combat resolution
        for p_id, forces in queued_combats.items():
            self._resolve_combat(p_id, forces)
            
    def _resolve_combat(self, p_id, forces):
        p = self.planets[p_id]
        forces[p["owner"]] += p["ships"]
        
        sorted_forces = sorted(forces.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_forces) == 1:
            p["owner"] = sorted_forces[0][0]
            p["ships"] = sorted_forces[0][1]
        else:
            top_owner, top_ships = sorted_forces[0]
            sec_owner, sec_ships = sorted_forces[1]
            
            survivors = top_ships - sec_ships
            if survivors == 0:
                p["owner"] = -1
                p["ships"] = 0
            else:
                p["owner"] = top_owner
                p["ships"] = survivors



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



CUSTOM_WEIGHTS = {"alpha": 12.989837726043973, "beta": 0.6517052557438298, "gamma": 1.755443882883826, "early_prod": 19.541064085088347, "mid_def": 15.467696793480005, "late_agg": 25.097210080379742}

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


