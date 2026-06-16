import os
import subprocess
import shutil

# First make sure kaggle.json is in the right place if it exists locally
local_kaggle_json = "kaggle.json"
kaggle_dir = os.path.expanduser("~/.kaggle")
target_kaggle_json = os.path.join(kaggle_dir, "kaggle.json")

if os.path.exists(local_kaggle_json):
    os.makedirs(kaggle_dir, exist_ok=True)
    shutil.copy(local_kaggle_json, target_kaggle_json)
    os.chmod(target_kaggle_json, 0o600)
    print("Copied kaggle.json to ~/.kaggle/kaggle.json")

if not os.path.exists(target_kaggle_json):
    print("ERROR: kaggle.json not found!")
    print("Please download it from your Kaggle Account settings and place it in this directory.")
    exit(1)

dataset = "kaggle/orbit-wars-episodes"
print(f"Downloading dataset {dataset}...")
# Depending on the exact dataset name. The user provided: "kaggle/orbit-wars-episodes-index"
dataset_name = "kaggle/orbit-wars-episodes-index"

try:
    subprocess.run(["python3", "-m", "kaggle", "datasets", "download", "-d", dataset_name, "-p", "./data", "--unzip"], check=True)
    print("Download complete!")
except Exception as e:
    print(f"Error downloading: {e}")
