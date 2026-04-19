from flask import Flask, jsonify
from flask_cors import CORS
import os

from db import init_db
from routes.auth import auth_bp
from routes.beans import beans_bp
from routes.shots import shots_bp
from routes.recommend import recommend_bp


def create_app():
    app = Flask(__name__)

    frontend_url = os.environ.get('FRONTEND_URL', 'https://grind-advisor-pro-test.vercel.app')
    CORS(app, origins=[frontend_url], supports_credentials=True)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(beans_bp, url_prefix='/api/beans')
    app.register_blueprint(shots_bp, url_prefix='/api/shots')
    app.register_blueprint(recommend_bp, url_prefix='/api')

    @app.route('/')
    def home():
        return jsonify({'status': 'ok', 'service': 'grind-advisor-api'})

    @app.route('/health')
    def health():
        return '', 204

    init_db()
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
