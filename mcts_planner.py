import math
import time
import random
from simulator import Simulator
from ml_planner import MLPlanner

# UCT Constant
C_PUCT = 1.5
SIMULATION_DEPTH = 15

class MCTSNode:
    def __init__(self, state, player_id, parent=None, move=None, prior_prob=1.0):
        self.state = state  # Simulator instance
        self.player_id = player_id
        self.parent = parent
        self.move = move # Action that led here
        
        self.children = []
        self.visits = 0
        self.value_sum = 0
        self.prior = prior_prob
        self.is_expanded = False
        
    @property
    def q_value(self):
        if self.visits == 0:
            return 0
        return self.value_sum / self.visits

class MCTSPlanner:
    def __init__(self, game_state, max_time=0.9):
        self.game_state = game_state
        self.max_time = max_time
        self.ml_planner = MLPlanner(game_state)
        self.root = MCTSNode(Simulator(game_state), game_state.player_id)
        
    def _evaluate_state(self, sim, player_id):
        # Quick heuristic evaluation at leaf
        my_ships = sum(p["ships"] for p in sim.planets.values() if p["owner"] == player_id)
        my_ships += sum(f["ships"] for f in sim.fleets if f["owner"] == player_id)
        
        enemy_ships = sum(p["ships"] for p in sim.planets.values() if p["owner"] not in (-1, player_id))
        enemy_ships += sum(f["ships"] for f in sim.fleets if f["owner"] not in (-1, player_id))
        
        diff = my_ships - enemy_ships
        # Squash to -1 to 1
        return math.tanh(diff / 100.0)

    def generate_moves(self):
        start_time = time.time()
        
        # Initial expansion
        self._expand(self.root)
        
        # If no moves proposed by Neural Net, return empty
        if not self.root.children:
            return []
            
        iterations = 0
        while time.time() - start_time < self.max_time:
            # 1. Select
            node = self._select(self.root)
            
            # 2. Expand & Evaluate
            if not node.is_expanded:
                self._expand(node)
                
            # 3. Simulate (Rollout)
            val = self._simulate(node.state)
            
            # 4. Backpropagate
            self._backpropagate(node, val)
            iterations += 1
            
        # Select best child based on visits (most robust)
        best_child = max(self.root.children, key=lambda c: c.visits)
        # Returns a single compound move (list of launches)
        return best_child.move

    def _select(self, node):
        while node.is_expanded and node.children:
            best_score = -float('inf')
            best_child = None
            for child in node.children:
                # PUCT formula
                u = C_PUCT * child.prior * math.sqrt(node.visits + 1e-8) / (1 + child.visits)
                score = child.q_value + u
                if score > best_score:
                    best_score = score
                    best_child = child
            node = best_child
        return node

    def _expand(self, node):
        node.is_expanded = True
        
        # Get prior probabilities from Neural Network for this specific state
        # We temporarily hijack MLPlanner's state to match the simulation
        # In a perfect world we build a GameState wrapper, but MLPlanner is flexible enough
        original_state = self.ml_planner.state
        
        # We need a mock GameState that MLPlanner can read
        class MockState: pass
        mock_state = MockState()
        mock_state.player_id = node.player_id
        
        # Build mock planets and fleets for MLPlanner
        class MockPlanet: pass
        mock_state.planets = {}
        for p_id, p_data in node.state.planets.items():
            mp = MockPlanet()
            mp.id = p_id
            mp.owner = p_data["owner"]
            mp.x = p_data["x"]
            mp.y = p_data["y"]
            mp.ships = p_data["ships"]
            mp.production = p_data["production"]
            mock_state.planets[p_id] = mp
            
        class MockFleet: pass
        mock_state.fleets = []
        for f_data in node.state.fleets:
            mf = MockFleet()
            mf.owner = f_data["owner"]
            mf.x = f_data["x"]
            mf.y = f_data["y"]
            mf.angle = f_data["angle"]
            mf.ships = f_data["ships"]
            mock_state.fleets.append(mf)
            
        self.ml_planner.state = mock_state
        base_moves = self.ml_planner.generate_moves() # List of (p_id, angle, ships)
        self.ml_planner.state = original_state
        
        if not base_moves:
            return
            
        # Neural Network proposes a primary compound move.
        # We will generate variations (mutations) of this move for MCTS to explore.
        # Variation 1: The exact NN move (Prior=0.5)
        self._add_child(node, base_moves, prior=0.5)
        
        # Variation 2-5: Randomly perturbed angles or ships (Priors=0.1)
        for _ in range(5):
            mutated_moves = []
            for m in base_moves:
                if random.random() < 0.5:
                    new_angle = m[1] + random.uniform(-0.2, 0.2)
                    new_ships = max(1, int(m[2] * random.uniform(0.8, 1.2)))
                    mutated_moves.append((m[0], new_angle, new_ships))
                else:
                    mutated_moves.append(m)
            self._add_child(node, mutated_moves, prior=0.1)
            
    def _add_child(self, node, moves, prior):
        # Create a new simulator and apply the moves
        new_sim = node.state.clone()
        for m in moves:
            try:
                new_sim.add_launch(m[0], m[1], m[2])
            except KeyError:
                pass # Planet might not exist
        # Advance 1 step
        new_sim._step()
        new_sim.step += 1
        
        child = MCTSNode(new_sim, node.player_id, parent=node, move=moves, prior_prob=prior)
        node.children.append(child)

    def _simulate(self, sim):
        rollout_sim = sim.clone()
        rollout_sim.simulate_ahead(SIMULATION_DEPTH)
        return self._evaluate_state(rollout_sim, self.root.player_id)

    def _backpropagate(self, node, value):
        while node is not None:
            node.visits += 1
            node.value_sum += value
            node = node.parent
