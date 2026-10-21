"""Data preparation shared by training (main.py) and tuning (tuning.py)."""

import pandas as pd

from config import (
    DATA_PATH,
    FORECAST_HORIZON,
    INPUT_SEQUENCE_LENGTH,
    TEMPERATURE_COLUMN,
    TIMESTAMP_COLUMN,
    TRAIN_RATIO,
    VALIDATION_RATIO,
)
from data_loading import load_weather_data
from preprocessing import (
    MyScaler,
    find_end_points,
    create_sequences,
    split_sequences,
)


def prepare_data():
    """Load, scale and split the data into model-ready sequences.

    Returns the raw data (needed for test timestamps), the scaler, and the
    train/validation/test sequences.
    """
    data = load_weather_data(DATA_PATH, TIMESTAMP_COLUMN, TEMPERATURE_COLUMN)
    temperature = data[TEMPERATURE_COLUMN].to_numpy()

    boundaries = find_end_points(data, TRAIN_RATIO, VALIDATION_RATIO)

    scaler = MyScaler.from_values(temperature[:boundaries["train_end"]])
    scaled_temperature = scaler.scale(temperature)

    X, y, target_indices = create_sequences(
        scaled_temperature, INPUT_SEQUENCE_LENGTH, FORECAST_HORIZON
    )
    sequences = split_sequences(X, y, target_indices, boundaries)
    return data, scaler, sequences