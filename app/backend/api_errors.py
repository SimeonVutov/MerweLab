"""Consistent JSON errors while preserving HTTP status codes and headers."""
from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException

from weather_queries import InvalidQuery


def invalid_query(error):
    return jsonify({'error': str(error)}), 400


def http_error(error):
    response = error.get_response()
    response.data = current_app.json.dumps({'error': error.description})
    response.content_type = 'application/json'

    return response


def missing_archive(error):
    current_app.logger.error('The committed weather archive could not be found')

    return jsonify({'error': 'Historical weather data is unavailable on the server'}), 503


def server_error(error):
    current_app.logger.exception('Weather request failed')

    return jsonify({'error': 'The server could not process the weather request'}), 500


def register_error_handlers(app):
    app.register_error_handler(InvalidQuery, invalid_query)
    app.register_error_handler(HTTPException, http_error)
    app.register_error_handler(FileNotFoundError, missing_archive)
    app.register_error_handler(Exception, server_error)
