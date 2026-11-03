"""Validate history filters and aggregate observations for JSON responses."""
from datetime import datetime, timedelta
import math

from weather_data import OBSERVATION_INTERVAL, UTC, VARIABLES, format_time, observation_slice

AGGREGATIONS = ('10min', 'hour', 'day', 'month')
MAX_POINTS = 2000


class InvalidQuery(ValueError):
    pass


def parse_time(text, name):
    try:
        value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except (TypeError, ValueError):
        raise InvalidQuery(f'{name} must be an ISO date or datetime') from None

    # Date-only controls and datetimes without an offset are explicitly UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def validate_query_parameters(arguments):
    allowed_arguments = {'start', 'end', 'aggregation', 'fields'}
    if set(arguments) - allowed_arguments:
        raise InvalidQuery('Allowed parameters: start, end, aggregation, fields')

    repeated_parameters = any(len(arguments.getlist(name)) != 1 for name in arguments)
    if repeated_parameters:
        raise InvalidQuery('Each query parameter must occur only once')


def parse_date_range(arguments, archive):
    end = datetime.fromtimestamp(archive.timestamps[-1] + OBSERVATION_INTERVAL, UTC)
    if 'end' in arguments:
        end = parse_time(arguments['end'], 'end')

    if 'start' in arguments:
        start = parse_time(arguments['start'], 'start')
    else:
        start = default_start_time(end)

    if start >= end:
        raise InvalidQuery('start must be earlier than end; end is exclusive')

    return start, end


def default_start_time(end):
    try:
        return end - timedelta(days=7)
    except OverflowError:
        raise InvalidQuery('end is too early for the default seven-day range') from None


def parse_aggregation(arguments):
    aggregation = arguments.get('aggregation', 'hour')
    if aggregation not in AGGREGATIONS:
        raise InvalidQuery(f'aggregation must be one of: {", ".join(AGGREGATIONS)}')

    return aggregation


def parse_fields(arguments):
    fields = list(VARIABLES)
    if 'fields' in arguments:
        fields = [field.strip() for field in arguments['fields'].split(',')]

    has_duplicates = len(fields) != len(set(fields))
    has_unknown_fields = any(field not in VARIABLES for field in fields)
    if not fields or has_duplicates or has_unknown_fields:
        raise InvalidQuery(f'fields must be unique names from: {", ".join(VARIABLES)}')

    return fields


def parse_history_query(arguments, archive):
    validate_query_parameters(arguments)

    start, end = parse_date_range(arguments, archive)
    aggregation = parse_aggregation(arguments)
    fields = parse_fields(arguments)

    return start, end, aggregation, fields


def bucket_start(moment, aggregation):
    if aggregation == 'month':
        return moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if aggregation == 'day':
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)

    if aggregation == 'hour':
        return moment.replace(minute=0, second=0, microsecond=0)

    return moment.replace(minute=moment.minute // 10 * 10, second=0, microsecond=0)


def next_bucket(moment, aggregation):
    if aggregation == 'month':
        if moment.month == 12:
            return moment.replace(year=moment.year + 1, month=1)

        return moment.replace(month=moment.month + 1)

    duration = {
        '10min': timedelta(minutes=10),
        'hour': timedelta(hours=1),
        'day': timedelta(days=1),
    }
    return moment + duration[aggregation]


def checked_next_bucket(moment, aggregation):
    try:
        return next_bucket(moment, aggregation)
    except (OverflowError, ValueError):
        raise InvalidQuery('Date range is outside supported calendar bounds') from None


def make_buckets(start, end, aggregation):
    boundaries = []
    current = bucket_start(start, aggregation)

    while current < end:
        if len(boundaries) >= MAX_POINTS:
            raise InvalidQuery('Requested range exceeds 2000 points; use coarser aggregation or a shorter range')

        following = checked_next_bucket(current, aggregation)
        boundaries.append((current, following))
        current = following

    return boundaries


def field_statistics(values, first, stop):
    valid_values = [value for value in values[first:stop] if math.isfinite(value)]
    valid_count = len(valid_values)
    missing_count = stop - first - valid_count

    if not valid_values:
        return {
            'validCount': 0,
            'missingCount': missing_count,
            'mean': None,
            'minimum': None,
            'maximum': None,
        }

    return {
        'validCount': valid_count,
        'missingCount': missing_count,
        'mean': math.fsum(valid_values) / valid_count,
        'minimum': min(valid_values),
        'maximum': max(valid_values),
    }


def summarize_range(archive, start, end, fields):
    first, stop = observation_slice(archive, start, end)
    observation_count = stop - first

    # Count absent ten-minute slots within the requested interval separately
    # from missing values in the rows that actually exist.
    interval_start = math.ceil(start.timestamp() / OBSERVATION_INTERVAL)
    interval_end = math.ceil(end.timestamp() / OBSERVATION_INTERVAL)
    expected_count = interval_end - interval_start

    first_observation = None
    last_observation = None
    if observation_count > 0:
        first_observation = format_time(archive.timestamps[first])
        last_observation = format_time(archive.timestamps[stop - 1])

    statistics = {
        field: field_statistics(archive.values[field], first, stop)
        for field in fields
    }

    return {
        'observationCount': observation_count,
        'expectedObservationCount': expected_count,
        'missingObservationCount': expected_count - observation_count,
        'firstObservation': first_observation,
        'lastObservation': last_observation,
        'fields': statistics,
    }


def aggregate_bucket(archive, start, end, fields, label):
    first, stop = observation_slice(archive, start, end)
    result = {'time': label, 'sampleCount': stop - first, 'validCounts': {}}

    for field in fields:
        statistics = field_statistics(archive.values[field], first, stop)

        result['validCounts'][field] = statistics['validCount']
        result[field] = statistics['mean']
        if VARIABLES[field]['aggregation'] == 'maximum':
            result[field] = statistics['maximum']

    return result


def history_response(archive, start, end, aggregation, fields):
    boundaries = make_buckets(start, end, aggregation)
    observations = []
    for bucket_begin, bucket_end in boundaries:
        clipped_start = max(start, bucket_begin)
        clipped_end = min(end, bucket_end)
        label = format_time(bucket_begin.timestamp())

        observation = aggregate_bucket(archive, clipped_start, clipped_end, fields, label)
        observations.append(observation)

    summary = summarize_range(archive, start, end, fields)

    return {
        'start': format_time(start.timestamp()),
        'endExclusive': format_time(end.timestamp()),
        'aggregation': aggregation,
        'timezone': 'UTC',
        'fields': {field: VARIABLES[field] for field in fields},
        'summary': summary,
        'observations': observations,
        'notes': [
            'Bucket times mark the beginning of each UTC interval.',
            'Partial first and last buckets contain only observations inside the requested range.',
            'Means use available values; maximum wind speed uses the maximum in each bucket.',
            'Empty buckets contain null values, not zero.',
        ],
    }
