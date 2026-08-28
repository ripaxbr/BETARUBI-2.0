"""Compatibility entrypoint for VPS/Gunicorn deployments."""
from app import app

application = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
