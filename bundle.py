import os
import re

FILES = [
    "constants.py",
    "geometry.py",
    "world_model.py",
    "simulator.py",
    "evaluator.py",
    "planner.py",
    "agent.py"
]

LOCAL_MODULES = [f.replace(".py", "") for f in FILES]

def bundle():
    imports = set()
    code_blocks = []
    
    for f in FILES:
        with open(f, "r") as fp:
            lines = fp.readlines()
            for line in lines:
                if line.startswith("import ") or line.startswith("from "):
                    # Skip local imports
                    is_local = False
                    for mod in LOCAL_MODULES:
                        if f"import {mod}" in line or f"from {mod} import" in line:
                            is_local = True
                            break
                    if not is_local:
                        imports.add(line.strip())
                else:
                    code_blocks.append(line)
            code_blocks.append("\n\n")
            
    import json
    try:
        with open("best_weights.json", "r") as f:
            best_weights = json.load(f)
    except:
        best_weights = {}

    code_text = "".join(code_blocks)
    if best_weights:
        code_text = re.sub(r'CUSTOM_WEIGHTS\s*=\s*\{[^\}]*\}', f'CUSTOM_WEIGHTS = {json.dumps(best_weights)}', code_text)

    with open("submission.py", "w") as fp:
        for imp in sorted(imports):
            fp.write(imp + "\n")
        fp.write("\n")
        fp.write(code_text)

if __name__ == "__main__":
    bundle()
