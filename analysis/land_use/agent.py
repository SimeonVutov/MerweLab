import numpy as np
from keras.src.optimizers import Adam
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.models import Sequential
from features import make_features


def build_model(n_features, n_classes, model_config):
    model = Sequential([
        Input((n_features,)),
        Dense(model_config.dense_neurons, activation="tanh"),
        Dense(n_classes),
    ])
    model.compile(optimizer=Adam(learning_rate=model_config.learning_rate), loss="mse")
    return model


def choose_actions(q_table, mask, epsilon):
    best_action = np.argmax(np.where(mask, q_table, -1e6), axis=-1)
    rand = np.random.rand(*mask.shape)
    rand[~mask] = -1
    random_action = np.argmax(rand, axis=-1)
    explore = np.random.rand(len(best_action)) < epsilon
    return np.where(explore, random_action, best_action)


def predict_map(model, state, allowed, n_classes):
    features = make_features(state, n_classes)
    allowed_mask = allowed[state]  # (height, width, n_classes)

    # only cells with more than one allowed class need the model
    rows, cols = np.nonzero(allowed_mask.sum(axis=-1) > 1)
    q_values = model.predict(features[rows, cols], batch_size=4096, verbose=0)

    new_state = state.copy()
    new_state[rows, cols] = choose_actions(q_values, allowed_mask[rows, cols], epsilon=0.0)
    return new_state