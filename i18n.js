"""
routes/beans.py – Bean management (CRUD)
"""

from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_db

beans_bp = Blueprint("beans", __name__)


@beans_bp.route("/", methods=["GET"])
@require_auth
def list_beans():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT b.id, b.name, b.roast, b.origin, b.created_at,
                       COUNT(s.id) as shot_count
                FROM beans b
                LEFT JOIN shots s ON s.bean_id = b.id
                WHERE b.user_id = %s
                GROUP BY b.id
                ORDER BY b.created_at DESC
            """, (g.user_id,))
            beans = [_serialize(dict(r)) for r in cur.fetchall()]
    return jsonify(beans)


@beans_bp.route("/", methods=["POST"])
@require_auth
def create_bean():
    data = request.get_json(silent=True) or {}
    name   = (data.get("name") or "").strip()
    roast  = data.get("roast", "medium")
    origin = (data.get("origin") or "").strip() or None

    if not name:
        return jsonify({"error": "Bean name is required"}), 400
    if roast not in ("light", "medium", "dark"):
        return jsonify({"error": "Roast must be light, medium, or dark"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO beans (user_id, name, roast, origin)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, roast, origin, created_at
            """, (g.user_id, name, roast, origin))
            bean = _serialize(dict(cur.fetchone()))
    return jsonify(bean), 201


@beans_bp.route("/<bean_id>", methods=["DELETE"])
@require_auth
def delete_bean(bean_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM beans WHERE id = %s AND user_id = %s RETURNING id",
                (bean_id, g.user_id)
            )
            if not cur.fetchone():
                return jsonify({"error": "Bean not found"}), 404
    return jsonify({"deleted": bean_id})


def _serialize(b: dict) -> dict:
    return {
        "id":          str(b["id"]),
        "name":        b["name"],
        "roast":       b["roast"],
        "origin":      b.get("origin"),
        "shot_count":  b.get("shot_count", 0),
        "created_at":  b["created_at"].isoformat() if b.get("created_at") else None,
    }
