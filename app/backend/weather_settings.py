"""Defaults for building and refreshing the persistent station archive."""
from datetime import datetime, timezone

HISTORY_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
UPDATE_INTERVAL_SECONDS = 600
