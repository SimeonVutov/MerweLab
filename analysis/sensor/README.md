# Structure 

Sensor assignment consists of two parts.
First the historical data has to be fetched from KNMI and saved.
Then, based on the historical data the LSTM model is created and saved.

## Data Fetching

In order to fetch data, first you need to paste your authentication token into a proper field in `edr_api.py`.
Then specify the date range you want to get, and the file. 

### How it works?

We're using EDR API to fetch data from only one sensor. The dataset used contains readings from every 10 minutes.
Thanks to that we don't need to get files with multiple readings, we just need a sensor id to get all the measurements.

It is not possible to fetch large data simultaneously. Therefore, the data is fetched monthly, and then merged into one huge dataframe.

### What data we gather?

We used _10-minute-in-situ-meteorological-observations_, so there are observations from every 10 minutes.
Main features we store are:
- Mean temperature throughout 10 minutes
- Humidity
- Air Pressure

For the historical data, we get readings from 1st of January 2012 to 1st of October 2026. This is 39,5 MB of raw data.

### Sensor used

We're using the sensor located in Rotterdam Airport

- Sensor name: "Rotterdam Airport"
- Sensor id: "0-20000-0-06344"

## Modelling

In order to model the data, first you need to specify the parameters in the `config.py`. Then just run `main.py`.
You'll get your new model and scalers.

# Model Optimization

_Throughout the training process, we used 0.7/0.2/0.1 split as train/validation/test data split_

## Feature Selection

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

## Input Size Selection

We decided to set INPUT_SIZE_LENGTH to 18. It means that the model takes observations within last 3 hours before the prediction is made.

## Hyperparameter Optimization for FORECAST_HORIZON = 6

In order to optimize hyperparameters there is `tuning.py`. Library used to optimized this is called optuna. Below you can see the result.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 3_1 | 224             | 128              | 0.25         | 256        | 20     | 4        | 0.0006447487694793648 | 18                    | 0.773798 | 0.833297  |
| 3_2 | 320             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.784782 | 0.846423  |


## Model for forecast horizon = 3 (30 minutes)

To keep everything the same the INPUT_SIZE_LENGTH is 18.

Again I used the `tuning.py` and these is my best result.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 4_1 | 224             | 160              | 0.25         | 256        | 20     | 4        | 0.0008210842167906902 | 18                    | 0.525221 | 0.571771  |
| 4_2 | 320             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.516917 | 0.559183  |
| 4_3 | 416             | 128              | 0.01         | 256        | 20     | 4        | 0.001                 | 18                    | 0.517498 | 0.560797  |

## Model for forecast horizon = 1 (10 minutes)

To keep everything the same the INPUT_SIZE_LENGTH is 18.

Again I used the `tuning.py` and these is my best result. Note that 5_1 is suggested by the optimizer, all other models are based on my parameters.

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Learning Rate         | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|-----------------------|----------|-----------|
| 5_1 | 224             | 192              | 0.2          | 256        | 20     | 4        | 0.0015147501360859895 | 18                    | 0.478729 | 0.522286  |
| 5_2 | 256             | 144              | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.354708 | 0.376104  |
| 5_3 | 320             | 96               | 0.15         | 256        | 20     | 4        | 0.001                 | 18                    | 0.352751 | 0.372160  |
| 5_4 | 352             | 96               | 0.1          | 256        | 20     | 4        | 0.001                 | 18                    | 0.333121 | 0.367017  |

# Reusing the model

To reuse the model run to load the model.
```python
import tensorflow as tf

tf.keras.models.load_model("<Path to the model>")
```

Then you have to scale the data using the scaler used for training
```python
from preprocessing import load_scalers

load_scalers("<Path to the scalers>")
```
This part can be changed so instead of using MyScaler we could use some existing MinMaxScaler with built-in save.
