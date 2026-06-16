import json
import glob
import os

logs = glob.glob(os.path.expanduser("~/Downloads/80002882-*.json"))
for log_file in sorted(logs):
    print(f"\n--- Checking {os.path.basename(log_file)} ---")
    try:
        with open(log_file, "r") as f:
            data = json.load(f)
            
        max_duration = 0
        total_duration = 0
        errs = set()
        
        for step in data:
            # step is a list containing the dict
            if isinstance(step, list) and len(step) > 0:
                step_data = step[0]
            else:
                step_data = step
                
            if not isinstance(step_data, dict):
                continue
                
            dur = step_data.get("duration", 0)
            max_duration = max(max_duration, dur)
            total_duration += dur
            
            stderr = step_data.get("stderr", "").strip()
            if stderr:
                errs.add(stderr)
                
        print(f"Steps recorded: {len(data)}")
        print(f"Max duration: {max_duration:.4f}s")
        print(f"Average duration: {total_duration/max(1, len(data)):.4f}s")
        if errs:
            print(f"STDERR Output Found:")
            for e in errs:
                print(f"  > {e}")
        else:
            print("No STDERR output.")
            
    except Exception as e:
        print(f"Error reading {log_file}: {e}")
