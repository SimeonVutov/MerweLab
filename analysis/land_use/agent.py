"""The Q-network and how it turns a map into a predicted map."""
import numpy as np
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

from constraints import enforce_constraints
from features import make_features


def build_model(n_features, n_classes, model_config):
    """Small MLP: cell features in, one Q-value per class out."""
    model = Sequential([
        Input((n_features,)),
        Dense(model_config.dense_neurons, activation="relu"),
        Dense(model_config.dense_neurons, activation="relu"),
        Dense(n_classes),
    ])
    model.compile(optimizer=Adam(learning_rate=model_config.learning_rate), loss="mse")
    return model


def choose_actions(q_table, mask, epsilon):
    """Epsilon-greedy per cell: the best allowed class, or with probability epsilon a random allowed class."""
    best_action = np.argmax(np.where(mask, q_table, -1e6), axis=-1)
    rand = np.random.rand(*mask.shape)
    rand[~mask] = -1  # disallowed classes can never win the random pick
    random_action = np.argmax(rand, axis=-1)
    explore = np.random.rand(len(best_action)) < epsilon
    return np.where(explore, random_action, best_action)


def predict_map(model, state, allowed, n_classes, enforce=True):
    """Greedy prediction for the whole map. With enforce=True the hard rules are repaired afterwards."""
    features = make_features(state, n_classes)
    allowed_mask = allowed[state]  # (height, width, n_classes)

    # only cells with more than one allowed class need the model
    rows, cols = np.nonzero(allowed_mask.sum(axis=-1) > 1)
    q_values = model.predict(features[rows, cols], batch_size=4096, verbose=0)

    new_state = state.copy()
    new_state[rows, cols] = choose_actions(q_values, allowed_mask[rows, cols], epsilon=0.0)

    if enforce:
        # Q-values for the whole map (-inf where a class is not allowed), used to repair the map where it breaks a hard rule
        q_full = np.full(state.shape + (n_classes,), -np.inf, dtype=np.float32)
        q_full[rows, cols] = np.where(allowed_mask[rows, cols], q_values, -np.inf)
        new_state = enforce_constraints(new_state, q_full, start=state)
    return new_state