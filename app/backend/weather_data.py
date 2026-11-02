"""Read station observations and publish immutable archive snapshots."""
from array import array
from bisect import bisect_left
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import math
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = Path(__file__).resolve().parent / 'data/weather/rotterdam_airport_weather.csv'
UTC = timezone.utc
OBSERVATION_INTERVAL = 600
STATION = {'id': '0-20000-0-06344', 'name': 'Rotterdam Airport'}
VARIABLES = {
    'temperature': {'label': 'Air temperature', 'unit': '°C', 'aggregation': 'mean'},
    'humidity': {'label': 'Relative humidity', 'unit': '%', 'aggregation': 'mean'},
    'pressure': {'label': 'Station air pressure', 'unit': 'hPa', 'aggregation': 'mean'},
    'average_wind_speed': {'label': 'Mean wind speed', 'unit': 'm/s', 'aggregation': 'mean'},
    'max_wind_speed': {'label': 'Maximum wind speed', 'unit': 'm/s', 'aggregation': 'maximum'},
}
ARCHIVE_LOCK = Lock()


@dataclass(frozen=True)
class WeatherArchive:
    timestamps: array
    values: dict[str, array]
    missing_counts: dict[str, int]
    gap_count: int
    missing_timestamps: int


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp, UTC).isoformat().replace('+00:00', 'Z')


def read_measurement(text):
    if not text or not text.strip():
        return math.nan

    value = float(text)
    if not math.isfinite(value):
        return math.nan

    return value


def parse_observation_time(text, previous_timestamp):
    observation_time = datetime.fromisoformat(text)
    if observation_time.tzinfo is None:
        raise ValueError('Archive timestamps must include a timezone')

    timestamp = observation_time.timestamp()
    if timestamp % OBSERVATION_INTERVAL != 0:
        raise ValueError('Archive observation is not on a ten-minute boundary')

    if previous_timestamp is not None and timestamp <= previous_timestamp:
        raise ValueError('Archive timestamps must be unique and increasing')

    return timestamp


def append_observation(row, timestamps, values, missing_counts):
    previous_timestamp = timestamps[-1] if timestamps else None
    timestamp = parse_observation_time(row['time'], previous_timestamp)
    timestamps.append(timestamp)

    for field in VARIABLES:
        value = read_measurement(row[field])
        values[field].append(value)

        if math.isnan(value):
            missing_counts[field] += 1


def count_observation_gaps(timestamps):
    # An absent record differs from a record containing a missing measurement.
    gap_count = 0
    missing_timestamps = 0

    for previous, current in zip(timestamps, timestamps[1:]):
        elapsed_seconds = current - previous
        if elapsed_seconds <= OBSERVATION_INTERVAL:
            continue

        gap_count += 1
        missing_timestamps += int(elapsed_seconds / OBSERVATION_INTERVAL) - 1

    return gap_count, missing_timestamps


@lru_cache(maxsize=1)
def read_archive():
    timestamps = array('d')
    values = {field: array('d') for field in VARIABLES}
    missing_counts = dict.fromkeys(VARIABLES, 0)

    if not HISTORY_PATH.exists():
        return WeatherArchive(timestamps, values, missing_counts, 0, 0)

    with HISTORY_PATH.open(newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        required_columns = {'time', *VARIABLES}
        if not required_columns.issubset(reader.fieldnames or []):
            raise ValueError('Weather archive is missing required columns')

        for row in reader:
            append_observation(row, timestamps, values, missing_counts)

    gap_count, missing_timestamps = count_observation_gaps(timestamps)

    return WeatherArchive(timestamps, values, missing_counts, gap_count, missing_timestamps)


def get_archive():
    # Flask can handle simultaneous requests. Only the first one should parse
    # the large CSV; subsequent requests share the read-only column arrays.
    with ARCHIVE_LOCK:
        return read_archive()


def archive_metadata(archive):
    start = None
    latest = None
    end = None
    if archive.timestamps:
        start = format_time(archive.timestamps[0])
        latest = format_time(archive.timestamps[-1])
        end = format_time(archive.timestamps[-1] + OBSERVATION_INTERVAL)

    return {
        'source': HISTORY_PATH.relative_to(ROOT).as_posix(),
        'station': STATION,
        'start': start,
        'lastObservation': latest,
        'endExclusive': end,
        'observationCount': len(archive.timestamps),
        'intervalMinutes': 10,
        'timezone': 'UTC',
        'missingValues': archive.missing_counts,
        'gapCount': archive.gap_count,
        'missingTimestamps': archive.missing_timestamps,
        'variables': VARIABLES,
        'notes': [
            'Station observations are retained at their original ten-minute resolution.',
            'Rotterdam Airport represents regional conditions, not measurements on the development site.',
            'No missing observations or values are interpolated.',
        ],
    }


def observation_slice(archive, start, end):
    first = bisect_left(archive.timestamps, start.timestamp())
    stop = bisect_left(archive.timestamps, end.timestamp())
    return first, stop
