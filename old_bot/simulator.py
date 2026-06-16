import math
from typing import List, Dict, Tuple
from collections import defaultdict
from geometry import line_intersects_circle, distance, predict_planet_pos
from constants import CENTER, SUN_RADIUS, get_fleet_speed

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
