"""Data preparation shared by training (main.py) and tuning (tuning.py)."""

import pandas as pd

from config import (
    DATA_PATH,
    FORECAST_HORIZON,
    INPUT_SEQUENCE_LENGTH,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    TIMESTAMP_COLUMN,
    TRAIN_RATIO,
    VALIDATION_RATIO,
)
from data_loading import load_weather_data
from preprocessing import (
    scale_features,
    find_end_points,
    create_sequences,
    split_sequences,
    fit_scalers
)


def prepare_data():
    """Load, scale and split the data into model-ready sequences.

    Returns the raw data (needed for test timestamps), the scaler, and the
    train/validation/test sequences.
    """
    data = load_weather_data(DATA_PATH, TIMESTAMP_COLUMN, FEATURE_COLUMNS)
    target = data[TARGET_COLUMN].to_numpy()

    boundaries = find_end_points(data, TRAIN_RATIO, VALIDATION_RATIO)

    scalers = fit_scalers(data, FEATURE_COLUMNS, boundaries["train_end"])
    target_scaler = scalers[TARGET_COLUMN]

    scaled_features = scale_features(data, FEATURE_COLUMNS, scalers)
    scaled_target = target_scaler.scale(target)

    X, y, target_indices = create_sequences(
        scaled_features, scaled_target, INPUT_SEQUENCE_LENGTH, FORECAST_HORIZON
    )
    sequences = split_sequences(X, y, target_indices, boundaries)
    return data, scalers, sequences