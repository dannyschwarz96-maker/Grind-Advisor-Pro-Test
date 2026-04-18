from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app, origins=[
    "https://grind-advisor-pro-test.vercel.app"
], supports_credentials=True)


@app.route("/")
def home():
    return "API running", 200


@app.route("/health")
def health():
    return "", 204


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    
    return jsonify({
        "message": "User registered",
        "data": data
    }), 201


if __name__ == "__main__":
    app.run(debug=True)
