from dataclasses import dataclass
from pathlib import Path

# Files
DATA_PATH = Path("../rotterdam_airport_weather.csv")
MODEL_PATH = Path("../LSTM_model_id_1_1.keras")
SCALER_PATH = Path("../scaler.json")

# Column names
TIMESTAMP_COLUMN = "time"
TEMPERATURE_COLUMN = "temperature"

# Seed
RANDOM_SEED = 42

# Data Split
TRAIN_RATIO = 0.6
VALIDATION_RATIO = 0.3

# Sequence Construction
FORECAST_HORIZON = 6
INPUT_SEQUENCE_LENGTH = 18

@dataclass(frozen=True)
class ModelConfig:
    """Hyperparameters for LSTM model"""
    lstm_neurons: int = 200
    dropout_rate: float = 0.25
    dense_neurons: int = 100
    epochs: int = 30
    batch_size: int = 512
    patience: int = 4
