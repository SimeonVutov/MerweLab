"""Request only the station observations needed for an archive update."""
from datetime import datetime

import requests

from weather_data import STATION, UTC

PARAMETERS = {
    'temperature': 'ta',
    'humidity': 'rh',
    'pressure': 'ps',
    'average_wind_speed': 'ff',
    'max_wind_speed': 'fx',
}
ENDPOINT = (
    'https://api.dataplatform.knmi.nl/edr/v1/collections/'
    f'10-minute-in-situ-meteorological-observations/locations/{STATION["id"]}'
)


def coverage_rows(coverage, start, end):
    timestamps = coverage['domain']['axes']['t']['values']
    ranges = coverage['ranges']
    observations = []

    for index, text in enumerate(timestamps):
        moment = datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(UTC)
        if moment < start or moment > end:
            continue

        row = {'time': moment.isoformat().replace('+00:00', 'Z')}
        for field, parameter in PARAMETERS.items():
            value = ranges[parameter]['values'][index]
            row[field] = '' if value is None else value

        observations.append(row)

    return observations


def fetch_window(session, token, start, end):
    response = session.get(
        ENDPOINT,
        params={
            'datetime': f'{start.isoformat()}/{end.isoformat()}',
            'parameter-name': ','.join(PARAMETERS.values()),
        },
        headers={'Authorization': token},
        timeout=(10, 60),
    )
    # Do not include headers or response bodies in errors or logs.
    if response.status_code != 200:
        raise RuntimeError(f'KNMI returned HTTP {response.status_code}')

    coverages = response.json().get('coverages', [])
    observations = []
    for coverage in coverages:
        observations.extend(coverage_rows(coverage, start, end))

    return observations


def fetch_observation_batches(token, start, end):
    current = start

    # Small requests also allow a server that was offline for months to catch up.
    with requests.Session() as session:
        while current < end:
            if current.month == 12:
                following = current.replace(year=current.year + 1, month=1, day=1)
            else:
                following = current.replace(month=current.month + 1, day=1)

            window_end = min(following, end)
            observations = {}
            for row in fetch_window(session, token, current, window_end):
                observations[row['time']] = row

            # Publish one month at a time so requests can read partial history
            # and an interrupted initial download can resume from saved data.
            yield window_end, [observations[key] for key in sorted(observations)]
            current = window_end
