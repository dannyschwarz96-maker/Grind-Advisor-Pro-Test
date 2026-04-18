"""
app.py – Grind Advisor Pro backend entry point

Render Free Tier notes:
  - Single worker (gunicorn --workers 1) to avoid model-store race conditions
  - DB init runs on startup (idempotent CREATE TABLE IF NOT EXISTS)
  - /health endpoint for frontend keep-alive ping (avoids cold starts during active use)
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from db import init_db
from routes.auth import auth_bp
from routes.beans import beans_bp
from routes.shots import shots_bp
from routes.recommend import recommend_bp

app = Flask(__name__)

# CORS: allow your Vercel frontend (set FRONTEND_URL env var in Render dashboard)
frontend_url = os.environ.get("FRONTEND_URL", "*")
CORS(app, origins=[frontend_url, "http://localhost:3000", "http://127.0.0.1:5500"],
     supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp,       url_prefix="/api/auth")
app.register_blueprint(beans_bp,      url_prefix="/api/beans")
app.register_blueprint(shots_bp,      url_prefix="/api/shots")
app.register_blueprint(recommend_bp,  url_prefix="/api")


@app.route("/health")
def health():
    """
    Lightweight health check.
    Frontend pings this on load to wake up the Render dyno.
    Returns 204 (no content) to minimize response size.
    """
    return "", 204


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# Initialize DB schema on startup
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"[WARNING] DB init failed: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
