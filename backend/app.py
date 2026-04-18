"""
Grind Advisor Pro – Backend Entry Point
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# DB + Routes
from db import init_db
from routes.auth import auth_bp
from routes.beans import beans_bp
from routes.shots import shots_bp
from routes.recommend import recommend_bp


# --------------------------------------------------
# Flask App
# --------------------------------------------------
app = Flask(__name__)


# --------------------------------------------------
# CORS CONFIG (IMPORTANT FOR VERCEL FRONTEND)
# --------------------------------------------------
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://grind-advisor-pro-test.vercel.app"
)

CORS(
    app,
    resources={r"/*": {
        "origins": [
            FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:5500"
        ]
    }},
    supports_credentials=True
)


# --------------------------------------------------
# REGISTER BLUEPRINTS
# --------------------------------------------------
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(beans_bp, url_prefix="/api/beans")
app.register_blueprint(shots_bp, url_prefix="/api/shots")
app.register_blueprint(recommend_bp, url_prefix="/api")


# --------------------------------------------------
# HEALTH CHECK (Render uptime / frontend ping)
# --------------------------------------------------
@app.route("/health")
def health():
    return "", 204


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    allowed_origins = [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:5500"
    ]

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# --------------------------------------------------
# DB INIT ON STARTUP
# --------------------------------------------------
with app.app_context():
    try:
        init_db()
        print("[INFO] Database initialized successfully")
    except Exception as e:
        print(f"[WARNING] DB init failed: {e}")


# --------------------------------------------------
# LOCAL DEV ONLY
# --------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
