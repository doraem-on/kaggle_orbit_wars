import torch
import math
import os
import sys

# Make sure we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from train_imitation import AdvancedPolicyNetwork, MAX_PLANETS

_cached_model = None

class MLPlanner:
    def __init__(self, game_state, model_path="advanced_model.pth"):
        global _cached_model
        self.state = game_state
        self.device = torch.device("cpu")
        
        if _cached_model is None:
            _cached_model = AdvancedPolicyNetwork().to(self.device)
            if os.path.exists(model_path):
                try:
                    _cached_model.load_state_dict(torch.load(model_path, map_location=self.device))
                    _cached_model.eval()
                except Exception as e:
                    print(f"Error loading model: {e}")
            else:
                print("Warning: model.pth not found, using uninitialized weights.")
                _cached_model.eval()
                
        self.model = _cached_model

    def generate_moves(self):
        if not self.model:
            return []
            
        state_vec = []
        planet_dict = {}
        
        # Build state vector matching train_imitation.py
        # Need to ensure we index planets consistently. 
        # In training, we iterated through obs["planets"].
        # Here we iterate through self.state.planets (which is a dict keyed by id)
        
        sorted_planets = sorted(self.state.planets.values(), key=lambda p: p.id)
        
        # Find strongest enemy to trick the Neural Network
        enemy_scores = {}
        for p in sorted_planets:
            if p.owner not in (-1, self.state.player_id):
                enemy_scores[p.owner] = enemy_scores.get(p.owner, 0) + p.ships
        
        strongest_enemy = None
        if enemy_scores:
            strongest_enemy = max(enemy_scores, key=enemy_scores.get)
            
        # Calculate incoming fleets per planet
        incoming_allied = {}
        incoming_enemy = {}
        for p in sorted_planets:
            incoming_allied[p.id] = 0
            incoming_enemy[p.id] = 0
            
        for f in self.state.fleets:
            fx, fy, angle = f.x, f.y, f.angle
            nx = fx + math.cos(angle) * 200
            ny = fy + math.sin(angle) * 200
            
            best_dist = float('inf')
            best_target = None
            for p in sorted_planets:
                dist = math.hypot(p.x - fx, p.y - fy)
                if dist < best_dist:
                    best_dist = dist
                    best_target = p.id
                    
            if best_target is not None:
                if f.owner == self.state.player_id:
                    incoming_allied[best_target] += f.ships
                else:
                    incoming_enemy[best_target] += f.ships
        
        for i in range(MAX_PLANETS):
            if i < len(sorted_planets):
                p = sorted_planets[i]
                
                # The Trick: Only the strongest opponent is "-1" (Enemy). Other players are "0" (Neutral).
                if p.owner == self.state.player_id:
                    owner_flag = 1
                elif p.owner == strongest_enemy:
                    owner_flag = -1
                else:
                    owner_flag = 0
                    
                my_inc = incoming_allied.get(p.id, 0)
                en_inc = incoming_enemy.get(p.id, 0)
                
                # [owner, x, y, ships, prod, my_incoming, enemy_incoming]
                state_vec.extend([owner_flag, p.x/100, p.y/100, p.ships/100, p.production/10, my_inc/100, en_inc/100])
                planet_dict[i] = p  # i is the index in the neural net output
            else:
                state_vec.extend([0, 0, 0, 0, 0, 0, 0])
                
        with torch.no_grad():
            x = torch.tensor([state_vec], dtype=torch.float32).to(self.device)
            preds = self.model(x).squeeze(0).numpy() # Shape [150]
            
        moves = []
        for i in range(MAX_PLANETS):
            if i in planet_dict:
                p = planet_dict[i]
                # Only act from our planets
                if p.owner == self.state.player_id and p.ships > 0:
                    idx = i * 3
                    cos_a = preds[idx]
                    sin_a = preds[idx+1]
                    ship_frac = preds[idx+2]
                    
                    # Convert cos/sin to angle
                    angle = math.atan2(sin_a, cos_a)
                    
                    # Sigmoid-like clamp for ship fraction, or just clip
                    ship_frac = max(0.0, min(1.0, ship_frac))
                    
                    # Only launch if fraction is significant
                    if ship_frac > 0.05:
                        ships_to_send = int(p.ships * ship_frac)
                        if ships_to_send > 0:
                            moves.append((p.id, angle, ships_to_send))
                            
        return moves
