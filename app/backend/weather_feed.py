"""Page original ten-minute observations for initial loads and delta updates."""
from bisect import bisect_right
import math

from weather_data import VARIABLES, format_time
from weather_queries import InvalidQuery, parse_time

PAGE_SIZE = 10000


def feed_bounds(arguments, archive):
    if set(arguments) - {'after', 'through'}:
        raise InvalidQuery('Allowed parameters: after, through')

    if any(len(arguments.getlist(name)) != 1 for name in arguments):
        raise InvalidQuery('Each query parameter must occur only once')

    start = 0
    stop = len(archive.timestamps)
    if 'after' in arguments:
        after = parse_time(arguments['after'], 'after').timestamp()
        start = bisect_right(archive.timestamps, after)

    if 'through' in arguments:
        through = parse_time(arguments['through'], 'through').timestamp()
        stop = bisect_right(archive.timestamps, through)

    return start, stop


def observation_row(archive, index):
    row = [format_time(archive.timestamps[index])]
    for field in VARIABLES:
        value = archive.values[field][index]
        row.append(value if math.isfinite(value) else None)

    return row


def observation_page(arguments, archive):
    start, stop = feed_bounds(arguments, archive)
    end = min(start + PAGE_SIZE, stop)

    # A fixed `through` timestamp keeps the initial multi-page download stable
    # even when the updater appends another observation during that download.
    return {
        'columns': ['time', *VARIABLES],
        'rows': [observation_row(archive, index) for index in range(start, end)],
        'hasMore': end < stop,
    }
