import sys

import pandas as pd
import requests

api_version = "v1"
collection = "10-minute-in-situ-meteorological-observations"
base_url = f"https://api.dataplatform.knmi.nl/edr/{api_version}/collections/{collection}"
# Paste your token here
token = None
headers = {"Authorization": token}


class EDR_API:
    def __init__(self):
        pass


    def get_metadata(self):
        r = requests.get(base_url, headers=headers)
        r.raise_for_status()
        return r.json()


    def get_locations(self):
        r = requests.get(f"{base_url}/locations", headers=headers)
        r.raise_for_status()
        return r.json()


    def get_location(self, location_id, params):
        r = requests.get(f"{base_url}/locations/{location_id}", params, headers=headers)
        r.raise_for_status()
        return r.json()



def main():
    if token is None:
        raise Exception("No token provided!")

    api = EDR_API()

    location_id = "0-20000-0-06344"

    start_date = "2012-01-01T00:00:00Z"
    end_date = "2026-10-01T00:00:00Z"

    # unfortunately it is not possible to get all
    starting_dates = pd.date_range(start=start_date, end=end_date, freq="MS", inclusive="left")

    all_dfs = []

    for starting_date in starting_dates:
        print(starting_date)
        ending_date = starting_date + pd.DateOffset(months=1)

        starting_date_str = starting_date.strftime("%Y-%m-%dT00:00:00Z")
        ending_date_str = ending_date.strftime("%Y-%m-%dT23:59:59Z")

        params = {
            "datetime": f"{starting_date_str}/{ending_date_str}",
            "parameter-name": "ta,rh,ff,fx,ps", # parameters requested: Mean air temperature at 1.5 m, relative humidity, average wind speed, max wind speed, air pressure at sensor level
        }
        try:
            data = api.get_location(location_id, params)

            coverages = data.get("coverages", [])
            if not coverages:
                print("No data returned; skipping month.")
                continue

            coverage = coverages[0]
            domain = coverage["domain"]
            ranges = coverage["ranges"]
            axes = domain["axes"]

            if "t" not in axes:
                print("No time axis; skipping month.")
                continue

            timestamps = pd.to_datetime(
                axes["t"]["values"], utc=True
            )

            df = pd.DataFrame({"time": timestamps})

            for variable, values in ranges.items():
                df[variable] = values["values"]

            all_dfs.append(df)

        except Exception as e:
            print(f"Error for {starting_date_str}: {e}")
            continue

    if not all_dfs:
        print("No data retrieved.")
        return

    merged_df = pd.concat(all_dfs, ignore_index=True)

    # Sort and remove any duplicate timestamps
    merged_df = (
        merged_df
        .drop_duplicates(subset="time")
        .sort_values("time")
        .reset_index(drop=True)
    )

    merged_df = merged_df.rename(columns={
        "ff": "average_wind_speed",
        "fx": "max_wind_speed",
        "ta": "temperature",
        "rh": "humidity",
        "ps": "pressure",
    })

    # Save one CSV file
    merged_df.to_csv(
        "../rotterdam_airport_weather.csv",
        index=False
    )

    print("\nDownload complete!")
    print("Shape:", merged_df.shape)
    print(merged_df.head())
    print("Saved to rotterdam_airport_weather.csv")


if __name__ == "__main__":
    sys.exit(main())