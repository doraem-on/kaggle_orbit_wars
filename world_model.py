from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from constants import get_fleet_speed, CENTER, ROTATION_RADIUS_LIMIT
from geometry import distance, predict_planet_pos

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
