
import os


os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from tensorflow.keras.models import Sequential
from tensorflow.keras.callbacks import (
    EarlyStopping
)
from tensorflow.keras.layers import (
    LSTM,
    Dense,
    Dropout
)


def create_model(input_length, model_config):
    model = Sequential(
        [LSTM(model_config.lstm_neurons, activation='tanh', input_shape=(input_length, 1)),
         Dropout(model_config.dropout_rate),
         Dense(model_config.dense_neurons, activation='relu'),
         Dense(1)]
    )
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae'],
    )
    return model

def train_model(model, x_train, y_train, x_validation, y_validation, model_config):
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=model_config.patience,
        restore_best_weights=True
    )
    history = model.fit(
        x_train,
        y_train,
        epochs=model_config.epochs,
        batch_size=model_config.batch_size,
        callbacks=[early_stopping],
        verbose=1,
        validation_data=(x_validation, y_validation),
    )
    return model, history


















