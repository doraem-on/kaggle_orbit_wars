<div align="center">
  
# 🪐 Orbit Wars: Deep Imitation Learning Bot
  
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red)
![Kaggle](https://img.shields.io/badge/Kaggle-Orbit%20Wars-00A65A)
![License](https://img.shields.io/badge/License-MIT-green)

A state-of-the-art Deep Neural Network agent designed to dominate the **Kaggle Orbit Wars** environment. This project utilizes Behavioral Cloning (Imitation Learning) to extract winning strategies from the top global leaderboard bots and orchestrate complex, multi-planet fleet attacks.

</div>

---

## 📖 Overview
Orbit Wars is a fast-paced, multi-agent space strategy game where players conquer planets, manage production economies, and dispatch fleets across a 2D coordinate space. 

This repository chronicles the evolution of our bot from a baseline `BeamSearchPlanner` (which scored 555 ELO) into a robust **PyTorch-powered Neural Network**. By mining a massive 20GB dataset of top-tier replays, the bot learned how to evaluate dynamic board states—including fleets in transit—and instantly predict high-confidence launch vectors.

---

## 🧠 Architecture & Pipeline

### 1. Multi-Core Data Ingestion (`parse_replays.py`)
To process the massive Kaggle episodic dataset, we built a highly optimized, `multiprocessing`-driven parser that saturates modern CPUs. 
- **Deep Feature Engineering**: The parser calculates Euclidean distances for all fleets currently in transit, aggregating `incoming_allied_ships` and `incoming_enemy_ships` for every planet. This grants the model foresight into battles that haven't resolved yet.
- **Scale**: Extracted **663,426** multi-action state vectors directly from winning bots.

### 2. Deep Policy Network (`train_imitation.py`)
The brain of the agent is an `AdvancedPolicyNetwork` written in PyTorch.
- **Topology**: A deep Multilayer Perceptron (`1024 -> 512 -> 256`) with `BatchNorm1d` and `Dropout(0.2)` to prevent overfitting on the massive dataset.
- **Input**: A dense 350-dimensional vector representing 50 planets (Ownership, Coordinates, Ships, Production, and Incoming Fleets).
- **Output**: A 150-dimensional vector predicting the `[Target Angle X, Target Angle Y, Ship Fraction]` for every planet we own simultaneously.
- **Optimization**: Utilizes `torch.set_num_threads(10)` and multi-worker `DataLoader` pipelines for rapid convergence (MSE Loss dropped to `0.0281`).

### 3. Real-time Inference (`ml_planner.py` & `agent.py`)
During live Kaggle matches, the `MLPlanner` takes the raw game observation, recalculates the fleet trajectory features on the fly, and runs a forward pass through the cached PyTorch `.pth` weights. It converts the network's output logits back into valid game actions in milliseconds.

---

## ⚙️ Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/doraem-on/kaggle_orbit_wars.git
   cd kaggle_orbit_wars
   ```

2. **Install Dependencies**
   ```bash
   pip install torch kaggle tqdm
   ```

3. **Fetch the Dataset**
   Ensure your `kaggle.json` credentials are in the root directory or your `~/.kaggle` folder, then run:
   ```bash
   python3 download_data.py
   ```

---

## 🚀 Running the Pipeline

**1. Extract Features:**
```bash
python3 parse_replays.py
```
*This will generate `training_data_v2.jsonl` utilizing all available CPU cores.*

**2. Train the Model:**
```bash
python3 train_imitation.py
```
*This will train the network over 5 epochs and output `advanced_model.pth`.*

**3. Evaluate Locally:**
```bash
python3 head_to_head.py
```
*Pits the newly trained ML bot against the old Heuristic baseline across 100 simulated matches.*

**4. Bundle for Kaggle:**
```bash
tar -czvf submission.tar.gz main.py planner.py ml_planner.py train_imitation.py world_model.py simulator.py evaluator.py geometry.py constants.py advanced_model.pth
```
*Upload `submission.tar.gz` to the Kaggle competition page.*

---

## 🔮 Future Work
- **Reinforcement Learning (PPO)**: Transition from Imitation Learning to Self-Play RL to discover strategies that humans and top bots haven't found yet.
- **Transformer Architecture**: Replace the MLP with an Attention-based mechanism to better handle variable numbers of planets and fleets without zero-padding.
- **Temporal Stacking**: Feed the network the last 3 turns of history to infer velocity trends.

---

<div align="center">
<i>Built for Kaggle Orbit Wars</i>
</div>
