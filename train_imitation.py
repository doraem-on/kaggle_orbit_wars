import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

MAX_PLANETS = 50

class OrbitDataset(Dataset):
    def __init__(self, jsonl_file):
        self.states = []
        self.targets = []
        self._load_data(jsonl_file)
        
    def _load_data(self, file_path):
        with open(file_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    self.states.append(data["state"])
                    self.targets.append(data["target"])
                except Exception:
                    pass

    def __len__(self):
        return len(self.states)

    def __getitem__(self, idx):
        return torch.tensor(self.states[idx], dtype=torch.float32), torch.tensor(self.targets[idx], dtype=torch.float32)

class AdvancedPolicyNetwork(nn.Module):
    def __init__(self, input_dim=MAX_PLANETS*7, output_dim=MAX_PLANETS*3):
        super().__init__()
        # Deeper and wider network with Batchnorm and Dropout for the larger dataset
        self.net = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            
            nn.Linear(256, output_dim)
        )
        
    def forward(self, x):
        return self.net(x)

def train():
    # Maximize CPU usage for PyTorch Math operations
    torch.set_num_threads(10)
    
    dataset = OrbitDataset("training_data_v2.jsonl")
    if len(dataset) == 0:
        print("No valid training data found.")
        return
        
    print(f"Dataset loaded: {len(dataset)} examples.")
    # num_workers > 0 lets the dataloader fetch batches in parallel CPU threads
    dataloader = DataLoader(dataset, batch_size=128, shuffle=True, num_workers=4)
    
    model = AdvancedPolicyNetwork()
    optimizer = optim.Adam(model.parameters(), lr=0.0005)
    criterion = nn.MSELoss()
    
    print("Starting Multi-Core Training...")
    for epoch in range(5):
        model.train()
        total_loss = 0
        for states, targets in dataloader:
            optimizer.zero_grad()
            preds = model(states)
            loss = criterion(preds, targets)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        print(f"Epoch {epoch+1}, Loss: {total_loss/len(dataloader):.4f}")
        
    torch.save(model.state_dict(), "advanced_model.pth")
    print("Model saved to advanced_model.pth")

if __name__ == "__main__":
    train()
