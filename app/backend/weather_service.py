"""Own KNMI synchronization, archive publication and cached forecast results."""
import atexit
from datetime import datetime
import os
from threading import Event, Lock, Thread
from time import monotonic

from dotenv import load_dotenv

from knmi_client import fetch_new_observations
from weather_data import (
    OBSERVATION_INTERVAL, ROOT, UTC, format_time, get_archive,
)
from weather_predictions import WeatherPredictor
from weather_storage import append_observations

UPDATE_INTERVAL_SECONDS = 600


class WeatherService:
    def __init__(self, logger):
        self.logger = logger
        self.predictor = WeatherPredictor()
        self.stop_event = Event()
        self.state_lock = Lock()
        self.thread = None
        self.state = {
            'enabled': False,
            'checking': False,
            'lastChecked': None,
            'lastSuccessfulCheck': None,
            'error': None,
        }
        self.forecast = {'available': False, 'reason': 'Forecasts are being prepared'}

    def snapshot(self):
        with self.state_lock:
            return {'sync': dict(self.state), 'forecast': self.forecast}

    def set_state(self, **changes):
        with self.state_lock:
            self.state.update(changes)

    def refresh_forecast(self):
        archive = get_archive()
        based_on = format_time(archive.timestamps[-1])
        if self.forecast.get('basedOn') == based_on:
            return

        try:
            result = self.predictor.predict(archive)
        except Exception as error:
            self.logger.warning('Weather prediction unavailable (%s)', type(error).__name__)
            result = {
                'available': False,
                'reason': 'Forecast unavailable: models or the latest three hours of inputs are incomplete',
            }

        with self.state_lock:
            self.forecast = result

    def synchronize(self, token):
        self.set_state(checking=True)
        try:
            archive = get_archive()
            start = datetime.fromtimestamp(archive.timestamps[-1] + OBSERVATION_INTERVAL, UTC)
            end = datetime.now(UTC)
            rows = fetch_new_observations(token, start, end)
            added = append_observations(rows)
            self.set_state(lastSuccessfulCheck=format_time(end.timestamp()), error=None)
            self.logger.info('KNMI synchronization added %s observations', added)
        except Exception as error:
            # Keep credentials and upstream payloads out of logs and responses.
            self.logger.warning('KNMI synchronization failed (%s)', type(error).__name__)
            self.set_state(error='KNMI update failed; stored observations remain available')
        finally:
            self.set_state(checking=False, lastChecked=format_time(datetime.now(UTC).timestamp()))

    def run(self, token):
        while not self.stop_event.is_set():
            started = monotonic()
            if token:
                self.synchronize(token)

            try:
                self.refresh_forecast()
            except Exception as error:
                self.logger.warning('Weather archive unavailable (%s)', type(error).__name__)

            # Fetching and inference time count towards the ten-minute interval.
            remaining = max(0, UPDATE_INTERVAL_SECONDS - (monotonic() - started))
            self.stop_event.wait(remaining)

    def start(self):
        if self.thread is not None:
            return

        load_dotenv(ROOT / '.env', override=False)
        token = os.getenv('EDR_API_TOKEN')
        self.set_state(enabled=bool(token))
        if not token:
            self.set_state(error='KNMI updates require EDR_API_TOKEN')

        self.thread = Thread(target=self.run, args=(token,), daemon=True, name='weather-updates')
        self.thread.start()
        atexit.register(self.stop_event.set)
