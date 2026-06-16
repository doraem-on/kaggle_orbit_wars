# Kaggle Orbit Wars Bot - Imitation Learning

This repository contains an advanced Imitation Learning bot designed to compete in the [Kaggle Orbit Wars](https://www.kaggle.com/competitions/orbit-wars) competition. 

The bot was transitioned from a rule-based `BeamSearchPlanner` heuristic to a state-of-the-art Deep Neural Network using Behavioral Cloning on the daily top-rated episodes dataset.

## Features
- **Automated Data Ingestion**: Seamlessly downloads Kaggle daily episode datasets containing thousands of high-ELO matches.
- **Multi-Core Data Parsing**: Uses `multiprocessing` to extract hundreds of thousands of state-action pairs in minutes.
- **Deep Feature Engineering**: Evaluates incoming allied and enemy fleets dynamically for every planet to make highly contextual decisions.
- **Multi-Action Prediction**: Predicts an independent target angle and ship launch fraction for up to 50 planets simultaneously.
- **PyTorch Optimization**: Trains a deep `AdvancedPolicyNetwork` (1024 -> 512 -> 256) utilizing native PyTorch multi-threading and `DataLoader` workers for maximum CPU efficiency.

## Repository Structure
- `agent.py` - The main entry point for the Kaggle environment.
- `ml_planner.py` - Translates live observation state into dense tensors and runs inference using the PyTorch model.
- `parse_replays.py` - Extracts training data from raw `.json` episode replays.
- `train_imitation.py` - Defines the `AdvancedPolicyNetwork` and runs the training loop.
- `world_model.py` / `simulator.py` - Local simulation environments.
- `head_to_head.py` - Local matchmaking to pit the new ML bot against baseline heuristic bots.

## Usage
1. Provide your Kaggle API credentials (`kaggle.json`).
2. Run `python3 download_data.py` (or `download_hub.py`) to fetch the top episodes.
3. Run `python3 parse_replays.py` to extract features into `training_data_v2.jsonl`.
4. Run `python3 train_imitation.py` to train `advanced_model.pth`.
5. Run `python3 bundle.py` or manually tar the files to create `submission.tar.gz`. Upload directly to Kaggle.
