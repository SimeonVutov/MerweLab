"""Validate new rows and atomically publish the updated CSV archive."""
import csv
from datetime import datetime
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile

from weather_data import (
    ARCHIVE_LOCK, HISTORY_PATH, VARIABLES, parse_observation_time,
    read_archive, read_measurement,
)


def validate_additions(rows, latest_timestamp):
    additions = []
    previous = latest_timestamp

    for row in rows:
        timestamp = datetime.fromisoformat(row['time']).timestamp()
        if timestamp <= latest_timestamp:
            continue

        previous = parse_observation_time(row['time'], previous)
        for field in VARIABLES:
            read_measurement(str(row[field]))

        additions.append(row)

    return additions


def write_updated_archive(additions):
    with HISTORY_PATH.open(encoding='utf-8', newline='') as source:
        columns = next(csv.reader(source))

    temporary_path = None
    try:
        # Copy old bytes unchanged. Atomic replacement protects the archive
        # if fetching, validation or writing fails before publication.
        with NamedTemporaryFile(dir=HISTORY_PATH.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            with HISTORY_PATH.open('rb') as source:
                shutil.copyfileobj(source, temporary)
                source.seek(-1, os.SEEK_END)
                if source.read(1) != b'\n':
                    temporary.write(b'\n')

        with temporary_path.open('a', encoding='utf-8', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writerows(additions)

        os.replace(temporary_path, HISTORY_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def append_observations(rows):
    if not rows:
        return 0

    # HTTP readers retain their immutable snapshot while the updater publishes
    # the next one. New requests see the new cache after publication.
    with ARCHIVE_LOCK:
        archive = read_archive()
        additions = validate_additions(rows, archive.timestamps[-1])
        if not additions:
            return 0

        write_updated_archive(additions)
        read_archive.cache_clear()

    return len(additions)
