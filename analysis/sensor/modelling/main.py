import os
from IPython.display import display

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import pandas as pd

import tensorflow as tf


from config import (
    DATA_PATH,
    FORECAST_HORIZON,
    INPUT_SEQUENCE_LENGTH,
    MODEL_PATH,
    RANDOM_SEED,
    TEMPERATURE_COLUMN,
    TIMESTAMP_COLUMN,
    TRAIN_RATIO,
    VALIDATION_RATIO,
    ModelConfig,
    SCALER_PATH,
)

from data_loading import (
    load_weather_data
)

from preprocessing import (
    MyScaler,
    find_end_points,
    create_sequences,
    split_sequences
)
from model_builder import (
    create_model,
    train_model
)

from plotting import (
    plot_series,
    plot_training_history,
    plot_forecast
)

from evaluation import (
    predict_original_scale,
    evaluate_forecast
)


# %% 0. Set seed
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)

model_config = ModelConfig()


# %% 1. Import and check data

data = load_weather_data(DATA_PATH, TIMESTAMP_COLUMN, TEMPERATURE_COLUMN)

# visualise_data(prepared_data[TIMESTAMP_COLUMN], prepared_data[TEMPERATURE_COLUMN],
#                "Time", "Temperature", "Temperature from data")

# %% 2. Find chronological splits

end_points = find_end_points(data, train_ratio=TRAIN_RATIO, val_ratio=VALIDATION_RATIO)


# %% Scale data to [0, 1]
scaler = MyScaler.from_values(data[TEMPERATURE_COLUMN][:end_points["train_end"]])
scaled_temperature = scaler.scale(data[TEMPERATURE_COLUMN].values)

# %% 4. Build sequences and split them

x_all, y_all, target_idx = create_sequences(
    scaled_temperature,
    INPUT_SEQUENCE_LENGTH,
    FORECAST_HORIZON
)

x_train, y_train, x_val, y_val, x_test, y_test, _, _, test_mask = split_sequences(x_all, y_all, target_idx, end_points)


print("Final X_train shape:", x_train.shape)
print("Final X_validation shape:", x_val.shape)
print("Final X_test shape:", x_test.shape)


# %% 5. Creating the temperature predicting LSTM model

model = create_model(INPUT_SEQUENCE_LENGTH, model_config)
model, history = train_model(model,x_train,y_train,x_val,y_val,model_config)

plot_training_history(history)


# %% 6. Evaluate all datasets

# set up the predictions:
y_train_actual = scaler.inverse_scale(y_train)
y_validation_actual = scaler.inverse_scale(y_val)
y_test_actual = scaler.inverse_scale(y_test)

train_pred = predict_original_scale(model, x_train, scaler)
validation_pred = predict_original_scale(model, x_val, scaler)
test_pred = predict_original_scale(model, x_test, scaler)

results = pd.DataFrame([
    evaluate_forecast(y_train_actual, train_pred, "Training"),
    evaluate_forecast(y_validation_actual, validation_pred, "Validation"),
    evaluate_forecast(y_test_actual, test_pred, "Test")
])

display(results)

# %% 7. Plot forecast comparison

# get timestamps of the test data
test_timestamps = (
    data
    .iloc[target_idx[test_mask]]
    [TIMESTAMP_COLUMN]
    .reset_index(drop=True)
)

comparison = pd.DataFrame({
    "timestamp": test_timestamps,
    "actual_temperature": y_test_actual,
    "predicted_temperature": test_pred
})

# Plot actual versus predicted air temperature

plot_forecast(comparison)
plot_forecast(comparison, 2000)

# %% 8. Save the model
model.save(MODEL_PATH)
scaler.save(SCALER_PATH)









