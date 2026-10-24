import pandas as pd

def load_weather_data(path, timestamp_column, feature_columns):

    data = pd.read_csv(path)
    data[timestamp_column] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
        utc=True,
    )
    return data[[timestamp_column, *feature_columns]].copy()