"""
routes/auth.py – Registration, login, profile
"""

import re
from flask import Blueprint, g, jsonify, request
from auth_utils import check_password, create_token, hash_password, require_auth
from db import get_db

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Validation
    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Valid email required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"error": "Email already registered"}), 409

            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at",
                (email, hash_password(password))
            )
            user = dict(cur.fetchone())

    token = create_token(str(user["id"]))
    return jsonify({"token": token, "user": _serialize_user(user)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()

    if not user or not check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(str(user["id"]))
    return jsonify({"token": token, "user": _serialize_user(dict(user))})


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, created_at FROM users WHERE id = %s",
                (g.user_id,)
            )
            user = cur.fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Shot + bean counts for dashboard
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as n FROM shots WHERE user_id = %s", (g.user_id,))
            shot_count = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) as n FROM beans WHERE user_id = %s", (g.user_id,))
            bean_count = cur.fetchone()["n"]

    u = _serialize_user(dict(user))
    u["shot_count"] = shot_count
    u["bean_count"] = bean_count
    return jsonify(u)


def _serialize_user(user: dict) -> dict:
    return {
        "id":         str(user["id"]),
        "email":      user["email"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
    }
