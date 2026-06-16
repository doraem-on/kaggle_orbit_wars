import kagglehub
import os
import shutil

print("Downloading dataset using kagglehub...")
# The token is read from ~/.kaggle/access_token or KAGGLE_API_TOKEN automatically
try:
    path = kagglehub.dataset_download("kaggle/orbit-wars-episodes-2026-06-15")
    print("Downloaded to:", path)
    
    # Move it to ./data
    dest = os.path.join(os.getcwd(), "data")
    if not os.path.exists(dest):
        os.makedirs(dest)
        
    print(f"Moving files from {path} to {dest}...")
    # kagglehub downloads to a cache dir. We copy the contents to ./data
    for item in os.listdir(path):
        s = os.path.join(path, item)
        d = os.path.join(dest, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
            
    print("Dataset ready in ./data!")
except Exception as e:
    print(f"Error downloading: {e}")
