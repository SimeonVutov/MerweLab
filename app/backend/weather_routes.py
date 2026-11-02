"""HTTP routes for historical weather resources."""
from flask import Blueprint, current_app, jsonify, request

from weather_data import STATION, archive_metadata, get_archive
from weather_feed import observation_page
from weather_queries import (
    AGGREGATIONS,
    MAX_POINTS,
    history_response,
    parse_history_query,
)

weather_api = Blueprint(
    'weather',
    __name__,
    url_prefix='/api/weather',
)


@weather_api.get('')
def weather_metadata():
    archive = get_archive()

    return jsonify({
        'history': archive_metadata(archive),
        'query': {
            'aggregations': AGGREGATIONS,
            'maximumPoints': MAX_POINTS,
            'default': 'Last seven archive days, aggregated hourly',
            'dateConvention': 'UTC; start inclusive and end exclusive',
        },
        **current_app.extensions['weather_service'].snapshot(),
    })


@weather_api.get('/history')
def weather_history():
    archive = get_archive()

    start, end, aggregation, fields = parse_history_query(request.args, archive)

    result = history_response(archive, start, end, aggregation, fields)
    result['station'] = STATION

    return jsonify(result)


@weather_api.get('/observations')
def weather_observations():
    archive = get_archive()
    page = observation_page(request.args, archive)

    return jsonify({
        **page,
        'history': archive_metadata(archive),
        **current_app.extensions['weather_service'].snapshot(),
    })
