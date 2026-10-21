from dataclasses import dataclass
from pathlib import Path

# Files
DATA_PATH = Path("../rotterdam_airport_weather.csv")
MODEL_PATH = Path("../LSTM_model_id_4_1.keras")
SCALER_PATH = Path("../scalers.json")

# Column names
TIMESTAMP_COLUMN = "time"
FEATURE_COLUMNS = ["temperature", "humidity", "pressure"]
TARGET_COLUMN = "temperature"
assert TARGET_COLUMN in FEATURE_COLUMNS, "TARGET_COLUMN must also be listed in FEATURE_COLUMNS"

# Seed
RANDOM_SEED = 42

# Data Split
TRAIN_RATIO = 0.7
VALIDATION_RATIO = 0.2

# Sequence Construction
FORECAST_HORIZON = 3
INPUT_SEQUENCE_LENGTH = 18

@dataclass(frozen=True)
class ModelConfig:
    """Hyperparameters for LSTM model"""
    lstm_neurons: int = 192
    dropout_rate: float = 0.0
    dense_neurons: int = 256
    epochs: int = 30
    batch_size: int = 256
    patience: int = 4
    learning_rate: float = 0.005603803105930284
