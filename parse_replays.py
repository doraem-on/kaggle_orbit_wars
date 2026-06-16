import os
import json
import glob
import multiprocessing
from tqdm import tqdm
import math

MAX_PLANETS = 50

def parse_single_replay(filepath):
    results = []
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except Exception:
        return results
        
    steps = data.get("steps", [])
    if not steps:
        return results
        
    # Find winner
    last_step = steps[-1]
    best_player = -1
    best_reward = -float('inf')
    
    for p_idx, p_data in enumerate(last_step):
        reward = p_data.get("reward", 0)
        if reward is not None and reward > best_reward:
            best_reward = reward
            best_player = p_idx
            
    if best_player == -1:
        return results
        
    for i, step in enumerate(steps[:-1]):
        if not isinstance(step, list):
            continue
            
        p_data = step[best_player]
        action_list = p_data.get("action", [])
        obs = p_data.get("observation", {})
        
        planets = obs.get("planets", [])
        fleets = obs.get("fleets", [])
        
        # Calculate incoming fleets per planet
        incoming_allied = {p[0]: 0 for p in planets}
        incoming_enemy = {p[0]: 0 for p in planets}
        
        for f in fleets:
            # f = [f_id, owner, x, y, angle, from_p_id, ships]
            # Fast target prediction using angle
            fx, fy, angle = f[2], f[3], f[4]
            nx = fx + math.cos(angle) * 200
            ny = fy + math.sin(angle) * 200
            
            best_dist = float('inf')
            best_target = None
            
            for p in planets:
                # p = [id, owner, x, y, radius, ships, production]
                px, py, pr = p[2], p[3], p[4]
                # Distance point to line segment roughly
                # Or just simple check if it intersects
                # This is an approximation for feature extraction
                dist_to_p = math.hypot(px - fx, py - fy)
                if dist_to_p < best_dist:
                    best_dist = dist_to_p
                    best_target = p[0]
                    
            if best_target is not None:
                if f[1] == best_player:
                    incoming_allied[best_target] += f[6]
                else:
                    incoming_enemy[best_target] += f[6]
        
        # Build state
        state_vec = []
        planet_dict = {}
        for idx in range(MAX_PLANETS):
            if idx < len(planets):
                p = planets[idx]
                p_id = p[0]
                owner_flag = 1 if p[1] == best_player else (-1 if p[1] != -1 else 0)
                my_inc = incoming_allied.get(p_id, 0)
                en_inc = incoming_enemy.get(p_id, 0)
                
                # [owner, x, y, radius, ships, prod, my_incoming, enemy_incoming]
                state_vec.extend([owner_flag, p[2]/100, p[3]/100, p[5]/100, p[6]/10, my_inc/100, en_inc/100])
                planet_dict[p_id] = p
            else:
                state_vec.extend([0, 0, 0, 0, 0, 0, 0])
                
        # Target [angle_x, angle_y, fraction] for every possible source planet
        target_vec = [0.0, 0.0, 0.0] * MAX_PLANETS
        if action_list:
            for act in action_list:
                src_id, angle, ships = act
                if src_id < MAX_PLANETS and src_id in planet_dict:
                    max_ships = max(1, planet_dict[src_id][5])
                    fraction = min(1.0, ships / max_ships)
                    idx = int(src_id) * 3
                    target_vec[idx] = math.cos(angle)
                    target_vec[idx+1] = math.sin(angle)
                    target_vec[idx+2] = fraction
                    
        # Filter: only learn from turns where an action was taken OR randomly sample non-actions
        if action_list or (i % 5 == 0): # keep 20% of no-action frames to learn when NOT to shoot
            results.append(json.dumps({
                "state": state_vec,
                "target": target_vec
            }))
            
    return results

def process_chunk(files_chunk):
    chunk_results = []
    for f in files_chunk:
        if "dataset-metadata" in f: continue
        res = parse_single_replay(f)
        chunk_results.extend(res)
    return chunk_results

def chunk_it(seq, num):
    avg = len(seq) / float(num)
    out = []
    last = 0.0
    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    return out

def main():
    data_dir = "./data"
    output_path = "training_data_v2.jsonl"
    
    replay_files = glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True)
    print(f"Found {len(replay_files)} replay files.")
    
    cores = min(10, multiprocessing.cpu_count())
    chunks = chunk_it(replay_files, cores)
    
    print(f"Parsing in parallel using {cores} CPU cores...")
    pool = multiprocessing.Pool(processes=cores)
    
    results = pool.map(process_chunk, chunks)
    
    total_extracted = 0
    with open(output_path, "w") as out_f:
        for chunk_res in results:
            for line in chunk_res:
                out_f.write(line + "\n")
                total_extracted += 1
                
    print(f"Extracted {total_extracted} state-action pairs to {output_path}")

if __name__ == "__main__":
    main()
