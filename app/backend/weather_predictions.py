"""Run the repository's trained LSTM models using their original feature scaling."""
import json
import math

from weather_data import ROOT, OBSERVATION_INTERVAL, format_time

MODEL_DIRECTORY = ROOT / 'analysis/sensor'
FEATURES = ('temperature', 'humidity', 'pressure')
SEQUENCE_LENGTH = 18
# Lowest documented test RMSE for each horizon in analysis/sensor/README.md.
MODEL_FILES = {
    10: ('LSTM_model_id_5_4.keras', 0.367017),
    30: ('LSTM_model_id_4_2.keras', 0.559183),
    60: ('LSTM_model_id_3_1.keras', 0.833297),
}


def validate_input(archive):
    timestamps = archive.timestamps[-SEQUENCE_LENGTH:]
    if len(timestamps) != SEQUENCE_LENGTH:
        raise ValueError('At least 18 observations are needed for a forecast')

    if any(b - a != OBSERVATION_INTERVAL for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError('The latest three hours contain missing observations')

    for field in FEATURES:
        if not all(math.isfinite(value) for value in archive.values[field][-SEQUENCE_LENGTH:]):
            raise ValueError('The latest three hours contain missing model inputs')


class WeatherPredictor:
    def __init__(self):
        self.models = {}
        self.scalers = None

    def load(self):
        if self.models:
            return

        import tensorflow as tf

        scalers = json.loads((MODEL_DIRECTORY / 'scalers.json').read_text())
        models = {}
        for horizon, (filename, _) in MODEL_FILES.items():
            model = tf.keras.models.load_model(MODEL_DIRECTORY / filename, compile=False)
            if model.input_shape != (None, SEQUENCE_LENGTH, len(FEATURES)):
                raise ValueError('Saved model input shape does not match the station features')

            models[horizon] = model

        self.scalers = scalers
        self.models = models

    def predict(self, archive):
        validate_input(archive)
        self.load()

        import numpy as np

        features = []
        for index in range(-SEQUENCE_LENGTH, 0):
            row = []
            for field in FEATURES:
                scaler = self.scalers[field]
                value = archive.values[field][index]
                row.append((value - scaler['min_value']) / (scaler['max_value'] - scaler['min_value']))

            features.append(row)

        model_input = np.asarray([features], dtype='float32')
        target_scaler = self.scalers['temperature']
        predictions = []
        for horizon, model in self.models.items():
            scaled = float(model(model_input, training=False).numpy()[0, 0])
            temperature = scaled * (target_scaler['max_value'] - target_scaler['min_value'])
            temperature += target_scaler['min_value']
            if not math.isfinite(temperature):
                raise ValueError('Model returned a non-finite prediction')

            predictions.append({
                'minutes': horizon,
                'time': format_time(archive.timestamps[-1] + horizon * 60),
                'temperature': temperature,
                'testRmse': MODEL_FILES[horizon][1],
            })

        return {
            'available': True,
            'basedOn': format_time(archive.timestamps[-1]),
            'predictions': predictions,
            'target': 'temperature',
            'unit': '°C',
        }
