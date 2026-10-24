import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error
)

def predict_original_scale(model, x, scaler):
    scaled_predictions = model.predict(x, verbose=0).flatten()
    return scaler.inverse_scale(scaled_predictions)

def evaluate_forecast(y_true, y_pred, dataset_name):
    mae =  mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    return {
        "Dataset": dataset_name,
        "MAE": mae,
        "RMSE": rmse,
    }
