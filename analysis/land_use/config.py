from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    """Hyperparameters for Q-Learning model"""
    dense_neurons: int = 100
    epochs: int = 20
    batch_size: int = 1
    learning_rate: float = 0.001