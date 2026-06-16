import time
from test_harness import MockObs, MockConfig
from agent import agent

obs = MockObs(step=100, planets=[
    [0, 0, 25, 80, 5, 100, 5], [1, 1, 75, 80, 5, 50, 5], [2, -1, 50, 85, 3, 10, 2],
])

actions = agent(obs, MockConfig())
print("Actions generated:", actions)
