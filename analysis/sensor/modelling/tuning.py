"""Hyperparameter search for the LSTM using Optuna.

Run with:  python tuning.py
Requires:  pip install optuna

Each trial trains a model with a different set of hyperparameters and is scored
by its best validation loss. The test set is never used here, so it stays an
honest final check.
"""
import numpy as np
import optuna
import tensorflow as tf

from config import RANDOM_SEED, ModelConfig
from model_builder import create_model, train_model
from pipeline import prepare_data

N_TRIALS = 5
STUDY_NAME = "lstm_temperature"
STORAGE = "sqlite:///optuna_study_60_min.db"  # lets you stop and resume the search


def suggest_config(trial: optuna.Trial) -> ModelConfig:
    """Define the search space: which values Optuna may try for each setting."""
    return ModelConfig(
        lstm_neurons=trial.suggest_int("lstm_units", 128, 256, step=32),
        dropout_rate=trial.suggest_float("dropout_rate", 0.0, 0.35, step=0.05),
        dense_neurons=trial.suggest_int("dense_units", 128, 256, step=32),
        batch_size=trial.suggest_categorical("batch_size", [256, 512, 1024, 2048]),
        learning_rate=trial.suggest_float("learning_rate", 5e-4, 2e-3, log=True),
    )


def objective(trial: optuna.Trial, x_train, y_train, x_validation, y_validation) -> float:
    """Train one model and return its best validation loss (lower is better)."""
    config = suggest_config(trial)

    tf.keras.backend.clear_session()  # free memory from previous trials
    np.random.seed(RANDOM_SEED)
    tf.random.set_seed(RANDOM_SEED)

    model = create_model(x_train.shape[1:], config)
    _, history = train_model(model, x_train, y_train, x_validation, y_validation, config, verbose=0)
    return min(history.history["val_loss"])


def main() -> None:
    _, _, sequences = prepare_data()

    x_train, y_train, x_validation, y_validation, _, _, _, _, _ = sequences

    study = optuna.create_study(
        study_name=STUDY_NAME,
        storage=STORAGE,
        load_if_exists=True,
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED),
    )
    study.optimize(lambda trial: objective(trial, x_train, y_train, x_validation, y_validation), n_trials=N_TRIALS)

    print("\nBest validation MSE (scaled):", study.best_value)
    print("Best hyperparameters:")
    for name, value in study.best_params.items():
        print(f"  {name}: {value}")


if __name__ == "__main__":
    main()