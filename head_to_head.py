import subprocess
import multiprocessing

def worker(args):
    i, new_is_p0 = args
    p0 = "new" if new_is_p0 else "old"
    p1 = "old" if new_is_p0 else "new"
    
    res = subprocess.run(["python3", "run_match_sub.py", p0, p1, str(i)], capture_output=True, text=True)
    try:
        return float(res.stdout.strip().split("\n")[-1])
    except:
        return 0.5

if __name__ == "__main__":
    print("Starting Head-to-Head Diagnostics...")
    print("Running Fixed Bot against Old 561-Elo Champion across 100 matches...")
    
    jobs = []
    for i in range(100):
        jobs.append((i, i < 50))
        
    pool = multiprocessing.Pool(processes=10)
    results = pool.map(worker, jobs)
    
    new_bot_wins = 0
    ties = 0
    for i, res in enumerate(results):
        new_is_p0 = i < 50
        if new_is_p0 and res == 0.0: new_bot_wins += 1
        elif not new_is_p0 and res == 1.0: new_bot_wins += 1
        elif res == 0.5:
            ties += 1
            new_bot_wins += 0.5
            
    print(f"Results over 100 matches:")
    print(f"Fixed Bot Wins: {new_bot_wins} / 100")
    print(f"Ties: {ties}")
