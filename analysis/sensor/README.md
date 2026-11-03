# KNMI observations and temperature prediction

This folder contains the sensor-data training workflow, saved LSTM models,
and scaling parameters. The web application's live service is implemented in
`app/backend/`; running the application does not retrain these models.

## Run the weather service

From the repository root:

```bash
uv sync --project app/backend
uv run --project app/backend python app/backend/server.py
```

Configure `EDR_API_TOKEN` in the repository-root `.env` file. Do not paste tokens
into Python source or commit them. See the [main setup guide](../../README.md#first-time-setup)
for frontend installation and KNMI configuration.

The backend stores its archive in
`app/backend/data/weather/rotterdam_airport_weather.csv`. If absent, it progressively
fetches observations from the start date in `app/backend/weather_settings.py`
(currently 1 January 2024). Existing archives are extended from their latest
observation; older gaps and earlier dates are not automatically backfilled.
It checks for new observations every ten minutes. The frontend loads the archive
in pages and then polls for new observations, normally once per minute.

The station is **Rotterdam Airport**, ID `0-20000-0-06344`. Stored observations are
ten minutes apart and include temperature, humidity, pressure, mean wind speed,
and maximum wind speed. Times use UTC. Missing observations remain missing.

CPU execution is supported; CUDA and a GPU are not required.

## Models used by the application

| Horizon | Saved model | Documented test RMSE, °C |
|---|---|---|
| 10 minutes | `LSTM_model_id_5_4.keras` | 0.367017 |
| 30 minutes | `LSTM_model_id_4_2.keras` | 0.559183 |
| 60 minutes | `LSTM_model_id_3_1.keras` | 0.833297 |

The models predict **temperature only** using temperature, humidity, and pressure
from the latest 18 consecutive observations. `scalers.json` supplies the original
training minima/maxima. The backend scales inputs and inverse-scales predictions.
A gap or missing input in that sequence makes the forecast unavailable.
The RMSE figures are saved experiment results, not live accuracy measurements.

## Train or tune a model

Training is separate from the app's persistent archive. The current training
configuration reads `analysis/sensor/rotterdam_airport_weather.csv`, not the
backend CSV. Set `DATA_PATH` explicitly if training from another archive.

Use a Python environment with TensorFlow, NumPy, pandas, Matplotlib, and IPython.
Optuna is additionally required for tuning. These analysis dependencies are not
all included in the backend environment.

Run from the modelling directory because its configured file paths are relative
to that working directory:

```bash
cd analysis/sensor/modelling
python main.py
```

Review `config.py` first: it controls the input CSV, sequence length, forecast
horizon, architecture, and output model/scaler paths. The current horizon of six
ten-minute steps predicts 60 minutes ahead. Choose output paths before running:
training saves the model and scalers and can overwrite existing files.

For hyperparameter search from the same directory:

```bash
python tuning.py
```

Check the study name, SQLite storage path and horizon before starting or resuming
a study. Changing a training output file does not automatically change which
models the backend selects; that mapping is in `app/backend/weather_predictions.py`.

## Recorded model experiments

The following tables preserve the original experiment record. The historical
training archive and the backend's continuously updated CSV are separate datasets.

### Model optimization

_Throughout the training process, we used 0.7/0.2/0.1 split as train/validation/test data split_

### Feature Selection

First thing to do is to check if adding more feature columns is worth it.

For forecast horizon = 6 (1 hour)
`FEATURE_COLUMNS = ['temperature']`

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|---------------|-----------------------|----------|-----------|
| 1_1 | 150             | 125              | 0.2          | 1024       | 30     | 4        | 0.001         | 18                    | ?        | ?         |

For forecast horizon = 6 (1 hour)
`FEATURE_COLUMNS = ['temperature', 'humidity', 'pressure']`

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|---------------|-----------------------|----------|-----------|
| 2_1 | 150             | 125              | 0.2          | 1024       | 30     | 4        | 0.001         | 18                    | ?        | ?         |

From the observations the conclusion is that adding more feature that may impact the temperature isn't making the model much worse but most likely it will be better (given 1_1 and 2_1 comparison).

### Input Size Selection

We decided to set INPUT_SIZE_LENGTH to 18. It means that the model takes observations within last 3 hours before the prediction is made.

### Hyperparameter Optimization for FORECAST_HORIZON = 6

In order to optimize hyperparameters there is `tuning.py`. Library used to optimized this is called optuna. Below you can see the result.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 3_1 | 224             | 128              | 0.25         | 256        | 20     | 4        | 0.0006447487694793648 | 18                    | 0.773798 | 0.833297  |
| 3_2 | 320             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.784782 | 0.846423  |


### Model for forecast horizon = 3 (30 minutes)

To keep everything the same the INPUT_SIZE_LENGTH is 18.

Again I used the `tuning.py` and these is my best result.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 4_1 | 224             | 160              | 0.25         | 256        | 20     | 4        | 0.0008210842167906902 | 18                    | 0.525221 | 0.571771  |
| 4_2 | 320             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.516917 | 0.559183  |
| 4_3 | 416             | 128              | 0.01         | 256        | 20     | 4        | 0.001                 | 18                    | 0.517498 | 0.560797  |

### Model for forecast horizon = 1 (10 minutes)

To keep everything the same the INPUT_SIZE_LENGTH is 18.

Again I used the `tuning.py` and these is my best result. Note that 5_1 is suggested by the optimizer, all other models are based on my parameters.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 5_1 | 224             | 192              | 0.2          | 256        | 20     | 4        | 0.0015147501360859895 | 18                    | 0.478729 | 0.522286  |
| 5_2 | 256             | 144              | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.354708 | 0.376104  |
| 5_3 | 320             | 96               | 0.15         | 256        | 20     | 4        | 0.001                 | 18                    | 0.352751 | 0.372160  |
| 5_4 | 352             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.333121 | 0.367017  |


## Reuse a saved model

Load with `tf.keras.models.load_model(path, compile=False)`. Match the original
feature order (temperature, humidity, pressure), apply the saved scalers, and
provide 18 consecutive observations at ten-minute intervals. Inverse-scale the
predicted temperature. The backend implementation in
`app/backend/weather_predictions.py` demonstrates this complete inference path.
