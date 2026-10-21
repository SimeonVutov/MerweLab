from IPython.core.completerlib import import_re

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
You'll get your new model and a scaler.

# Results

For forecast horizon = 6 (1 hour)

| ID  | Neurons in LSTM | Neurons in Dense | Dropout Rate | Batch Size | Epochs | Patience | Input Sequence Length | Val RMSE | Test RMSE |
|-----|-----------------|------------------|--------------|------------|--------|----------|-----------------------|----------|-----------|
| 1_1 | 200             | 100              | 0.25         | 512        | 30     | 4        | 18                    | 0.804687 | 0.877858  |
| 1_2 | 150             | 125              | 0.25         | 512        | 30     | 4        | 18                    | 0.822304         | 0.901983          |
| 1_3 | 192             | 256              | 0.0          | 256        | 30     | 4        | 18                    |          |           |

## Plots

### 1_1 Plots

![1_1_training_history.png](plots/1_1_training_history.png)
![1_1_predictions.png](plots/1_1_predictions.png)

# Reusing the model

To reuse the model run to load the model.
```python
import tensorflow as tf

tf.keras.models.load_model("<Path to the model>")
```

Then you have to scale the data using the scaler used for training
```python
from preprocessing import MyScaler

MyScaler.load("<Path to the scaler>")
```
This part can be changed so instead of using MyScaler we could use some existing MinMaxScaler with built-in save/

# Hyperparameter Tuning

In order to optimize hyperparameters there is `tuning.py`. Library used to optimized this is called optuna.

## Tuning Results

[I 2026-10-21 17:50:53,052] Trial 0 finished with value: 0.000485833763377741 and parameters: {'lstm_units': 128, 'dropout_rate': 0.5, 'dense_units': 224, 'batch_size': 4096, 'learning_rate': 0.0015930522616241021}. Best is trial 0 with value: 0.000485833763377741.
[I 2026-10-21 18:13:13,948] Trial 1 finished with value: 0.00021855589875485748 and parameters: {'lstm_units': 192, 'dropout_rate': 0.0, 'dense_units': 256, 'batch_size': 256, 'learning_rate': 0.0011207606211860567}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 18:21:35,479] Trial 2 finished with value: 0.00047213819925673306 and parameters: {'lstm_units': 160, 'dropout_rate': 0.15000000000000002, 'dense_units': 192, 'batch_size': 4096, 'learning_rate': 0.00025081156860452336}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 18:37:29,157] Trial 3 finished with value: 0.00023238276480697095 and parameters: {'lstm_units': 160, 'dropout_rate': 0.30000000000000004, 'dense_units': 64, 'batch_size': 4096, 'learning_rate': 0.004138040112561018}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 18:41:42,891] Trial 4 finished with value: 0.00031098563340492547 and parameters: {'lstm_units': 128, 'dropout_rate': 0.05, 'dense_units': 192, 'batch_size': 4096, 'learning_rate': 0.00032927591344236165}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 18:53:44,349] Trial 5 finished with value: 0.0004319701693020761 and parameters: {'lstm_units': 192, 'dropout_rate': 0.15000000000000002, 'dense_units': 160, 'batch_size': 1024, 'learning_rate': 0.006161049539380964}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 19:14:21,977] Trial 6 finished with value: 0.00024069567734841257 and parameters: {'lstm_units': 192, 'dropout_rate': 0.5, 'dense_units': 64, 'batch_size': 2048, 'learning_rate': 0.004544383960336014}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 19:19:31,981] Trial 7 finished with value: 0.0006139551987871528 and parameters: {'lstm_units': 128, 'dropout_rate': 0.15000000000000002, 'dense_units': 160, 'batch_size': 2048, 'learning_rate': 0.00024970737145052745}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 19:25:05,884] Trial 8 finished with value: 0.0005236372235231102 and parameters: {'lstm_units': 64, 'dropout_rate': 0.4, 'dense_units': 192, 'batch_size': 512, 'learning_rate': 0.005323617594751502}. Best is trial 1 with value: 0.00021855589875485748.
[I 2026-10-21 19:38:16,109] Trial 9 finished with value: 0.00026814237935468554 and parameters: {'lstm_units': 192, 'dropout_rate': 0.15000000000000002, 'dense_units': 64, 'batch_size': 4096, 'learning_rate': 0.0008798929749689024}. Best is trial 1 with value: 0.00021855589875485748.

Best validation MSE (scaled): 0.00021855589875485748
Best hyperparameters:
  lstm_units: 192
  dropout_rate: 0.0
  dense_units: 256
  batch_size: 256
  learning_rate: 0.0011207606211860567