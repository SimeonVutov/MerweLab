"""Local entry point for the MerweLab Flask API."""
from application import create_app

app = create_app()


if __name__ == '__main__':
    # Run one updater alongside the local server. Disabling the reloader avoids
    # starting another updater process when code changes.
    app.extensions['weather_service'].start()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, load_dotenv=False)
