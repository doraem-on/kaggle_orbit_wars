import math
from typing import Tuple

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
