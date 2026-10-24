import json
from pathlib import Path

import numpy as np


def find_end_points(data, train_ratio, val_ratio):
    data_size = len(data)
    train_end = int(data_size*train_ratio)
    val_end = int(data_size*(val_ratio + train_ratio))

    return {"train_end": train_end, "val_end": val_end, "test_end": data_size}

class MyScaler:
    def __init__(self, min_value, max_value):
        self.min_value = min_value
        self.max_value = max_value

    @classmethod
    def from_values(cls, values):
        """Build a scaler from the min/max of `values`."""
        return cls(np.nanmin(values), np.nanmax(values))

    def scale(self, x):
        return (x - self.min_value) / (self.max_value - self.min_value)

    def inverse_scale(self, y):
        return y * (self.max_value - self.min_value) + self.min_value

    def save(self, path) -> None:
        """Write the min and max to a  file."""
        content = {"min_value": float(self.min_value), "max_value": float(self.max_value)}
        Path(path).write_text(json.dumps(content, indent=2))

    @classmethod
    def load(cls, path: Path):
        """Load a scaler from a file."""
        content = json.loads(Path(path).read_text())
        return cls(content["min_value"], content["max_value"])

def fit_scalers(data, columns, train_end):
    return {
        column: MyScaler.from_values(data[column].to_numpy()[:train_end])
        for column in columns
    }

def scale_features(data, columns, scalers):
    return np.column_stack(
        [scalers[column].scale(data[column].to_numpy()) for column in columns]
    )

def save_scalers(path, scalers):
    content = {
        column: {"min_value": float(scaler.min_value), "max_value": float(scaler.max_value)}
        for column, scaler in scalers.items()
    }
    Path(path).write_text(json.dumps(content, indent=2))

def load_scalers(path):
    content = json.loads(Path(path).read_text())
    return {
        column: MyScaler(values["min_value"], values["max_value"])
        for column, values in content.items()
    }


def create_sequences(features, target, input_length, forecast_horizon):
    X = []
    y = []
    target_indices = []

    max_start = (
        len(features)
        - input_length
        - forecast_horizon
        + 1
    )

    for i in range(max_start):
        input_sequence = features[i:i + input_length]
        target_index = i + input_length + forecast_horizon - 1

        if (
            np.isnan(input_sequence).any()
            or np.isnan(target[target_index])
        ):
            continue

        X.append(input_sequence)
        y.append(target[target_index])
        target_indices.append(target_index)

    if not X:
        return (
            np.empty((0, input_length, features.shape[1])),
            np.empty((0,)),
            np.empty((0,), dtype=int),
        )

    return (
        np.array(X),
        np.array(y),
        np.array(target_indices, dtype=int)
    )

def split_sequences(X, Y, target_idx, end_points):
    train_mask = target_idx < end_points["train_end"]
    validation_mask = (
            (target_idx >= end_points["train_end"])
            & (target_idx < end_points["val_end"])
    )
    test_mask = target_idx >= end_points["val_end"]

    x_train = X[train_mask]
    y_train = Y[train_mask]

    x_validation = X[validation_mask]
    y_validation = Y[validation_mask]

    x_test = X[test_mask]
    y_test = Y[test_mask]

    return x_train, y_train, x_validation, y_validation, x_test, y_test, train_mask, validation_mask, test_mask