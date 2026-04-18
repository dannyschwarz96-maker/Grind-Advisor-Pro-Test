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

# ✅ EINZIGE CORS CONFIG
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Routes
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(beans_bp, url_prefix="/api/beans")
app.register_blueprint(shots_bp, url_prefix="/api/shots")
app.register_blueprint(recommend_bp, url_prefix="/api")

# Health
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# Root (optional)
@app.route("/")
def root():
    return jsonify({"message": "Backend running"}), 200

# Errors
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

# DB Init
with app.app_context():
    try:
        init_db()
        print("[INFO] Database initialized successfully")
    except Exception as e:
        print(f"[WARNING] DB init failed: {e}")

# Local dev
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
