```python
"""
Grind Advisor Pro – Backend Entry Point (Production Ready)
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://grind-advisor-pro-test.vercel.app"
)

ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:5500"
]

# --------------------------------------------------
# APP INIT
# --------------------------------------------------
app = Flask(__name__)

# --------------------------------------------------
# CORS (BASE CONFIG)
# --------------------------------------------------
CORS(
    app,
    resources={r"/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True
)

# --------------------------------------------------
# FORCE CORS HEADERS (CRITICAL FIX)
# --------------------------------------------------
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# --------------------------------------------------
# HANDLE PREFLIGHT (OPTIONS) GLOBALLY
# --------------------------------------------------
@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return "", 200


# --------------------------------------------------
# IMPORT ROUTES (AFTER APP INIT)
# --------------------------------------------------
from db import init_db
from routes.auth import auth_bp
from routes.beans import beans_bp
from routes.shots import shots_bp
from routes.recommend import recommend_bp

# --------------------------------------------------
# REGISTER BLUEPRINTS
# --------------------------------------------------
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(beans_bp, url_prefix="/api/beans")
app.register_blueprint(shots_bp, url_prefix="/api/shots")
app.register_blueprint(recommend_bp, url_prefix="/api")


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


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
```
