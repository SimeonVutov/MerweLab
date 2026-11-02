"""Create the Flask application and register its HTTP interface."""
from flask import Flask, jsonify

from api_errors import register_error_handlers
from weather_routes import weather_api
from weather_service import WeatherService


def index():
    return jsonify({
        'service': 'MerweLab weather API',
        'endpoints': [
            'GET /api/health',
            'GET /api/weather',
            'GET /api/weather/history?start=2026-09-01&end=2026-09-08&aggregation=hour',
        ],
    })


def health():
    return jsonify({'status': 'ok', 'service': 'MerweLab weather API'})


def create_app(config=None):
    app = Flask(__name__)
    app.json.sort_keys = False
    if config is not None:
        app.config.update(config)

    app.extensions['weather_service'] = WeatherService(app.logger)
    app.register_blueprint(weather_api)
    app.add_url_rule('/', view_func=index, methods=['GET'])
    app.add_url_rule('/api/health', view_func=health, methods=['GET'])
    register_error_handlers(app)

    return app
