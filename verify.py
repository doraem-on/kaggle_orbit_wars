import json
import multiprocessing
from tune import run_match

def worker(args):
    w0, w1, seed = args
    return run_match(w0, w1, seed)

if __name__ == "__main__":
    baseline_weights = {
        "alpha": 15.0,
        "beta": 0.5,
        "gamma": 2.0,
        "early_prod": 25.0,
        "mid_def": 15.0,
        "late_agg": 25.0
    }
    
    with open("best_weights.json", "r") as f:
        champion_weights = json.load(f)
        
    print("Verifying Champion vs Original Baseline...")
    
    jobs = []
    for i in range(5):
        jobs.append((champion_weights, baseline_weights, i)) # Champ is P0
        jobs.append((baseline_weights, champion_weights, i)) # Champ is P1
        
    pool = multiprocessing.Pool(processes=10)
    results = pool.map(worker, jobs)
    
    champ_wins = 0
    for i, res in enumerate(results):
        if i % 2 == 0 and res == 0: champ_wins += 1
        if i % 2 == 1 and res == 1: champ_wins += 1
        if res == 0.5: champ_wins += 0.5
        
    print(f"\nFinal Score against Original Baseline: {champ_wins}/10")
    pool.close()
    pool.join()
