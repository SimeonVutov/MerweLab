"""Local entry point for the MerweLab Flask API."""
from application import create_app

app = create_app()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, load_dotenv=False)
