"""
routes/shots.py – Shot CRUD + bulk JSON import
"""

from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_db
from ml.model_store import delete_model  # invalidate model on new shot

shots_bp = Blueprint("shots", __name__)


@shots_bp.route("/", methods=["GET"])
@require_auth
def list_shots():
    bean_id = request.args.get("bean_id")
    limit   = min(int(request.args.get("limit", 100)), 500)

    with get_db() as conn:
        with conn.cursor() as cur:
            if bean_id:
                cur.execute("""
                    SELECT s.*, b.name as bean_name, b.roast
                    FROM shots s LEFT JOIN beans b ON b.id = s.bean_id
                    WHERE s.user_id = %s AND s.bean_id = %s
                    ORDER BY s.created_at DESC LIMIT %s
                """, (g.user_id, bean_id, limit))
            else:
                cur.execute("""
                    SELECT s.*, b.name as bean_name, b.roast
                    FROM shots s LEFT JOIN beans b ON b.id = s.bean_id
                    WHERE s.user_id = %s
                    ORDER BY s.created_at DESC LIMIT %s
                """, (g.user_id, limit))
            shots = [_serialize(dict(r)) for r in cur.fetchall()]
    return jsonify(shots)


@shots_bp.route("/", methods=["POST"])
@require_auth
def create_shot():
    data = request.get_json(silent=True) or {}

    grind_size      = data.get("grind_size")
    extraction_time = data.get("extraction_time")

    if grind_size is None or extraction_time is None:
        return jsonify({"error": "grind_size and extraction_time are required"}), 400
    try:
        grind_size      = float(grind_size)
        extraction_time = float(extraction_time)
    except (ValueError, TypeError):
        return jsonify({"error": "grind_size and extraction_time must be numbers"}), 400

    if grind_size <= 0 or extraction_time <= 0:
        return jsonify({"error": "Values must be positive"}), 400

    brew_weight = _float_or_none(data.get("brew_weight"))
    dose        = _float_or_none(data.get("dose")) or 18.0
    bean_id     = data.get("bean_id") or None
    rating      = data.get("rating")
    notes       = (data.get("notes") or "").strip() or None

    if rating is not None:
        rating = int(rating)
        if not 1 <= rating <= 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shots
                  (user_id, bean_id, grind_size, extraction_time, brew_weight, dose, rating, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (g.user_id, bean_id, grind_size, extraction_time,
                  brew_weight, dose, rating, notes))
            shot = _serialize(dict(cur.fetchone()))

    # Invalidate cached model → will retrain on next recommendation request
    delete_model(g.user_id)

    return jsonify(shot), 201


@shots_bp.route("/<shot_id>", methods=["DELETE"])
@require_auth
def delete_shot(shot_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM shots WHERE id = %s AND user_id = %s RETURNING id",
                (shot_id, g.user_id)
            )
            if not cur.fetchone():
                return jsonify({"error": "Shot not found"}), 404
    delete_model(g.user_id)
    return jsonify({"deleted": shot_id})


@shots_bp.route("/import", methods=["POST"])
@require_auth
def import_shots():
    """
    Bulk import from Decent Espresso / generic JSON export.
    Expected format:
      { "shots": [ { "grind_size": 20, "extraction_time": 27, "brew_weight": 36 }, ... ] }
    OR Decent-style:
      { "datapoints": [...], "timeInShot": 27.3, "shotWeight": 36.1 }
    """
    data = request.get_json(silent=True) or {}
    shots_raw = []

    if "shots" in data and isinstance(data["shots"], list):
        shots_raw = data["shots"]
    elif "timeInShot" in data:
        # Single Decent shot
        shots_raw = [{
            "extraction_time": data.get("timeInShot"),
            "brew_weight":     data.get("shotWeight"),
            "grind_size":      data.get("grindSize") or data.get("grind_size"),
        }]
    else:
        return jsonify({"error": "Unrecognized format. Expected {shots:[...]} or Decent JSON"}), 400

    imported = 0
    skipped  = 0
    errors   = []

    with get_db() as conn:
        with conn.cursor() as cur:
            for i, s in enumerate(shots_raw):
                try:
                    grind = float(s.get("grind_size") or s.get("grindSize") or 0)
                    time  = float(s.get("extraction_time") or s.get("timeInShot") or 0)
                    if grind <= 0 or time <= 0:
                        skipped += 1
                        continue
                    cur.execute("""
                        INSERT INTO shots
                          (user_id, grind_size, extraction_time, brew_weight, dose, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        g.user_id,
                        grind,
                        time,
                        _float_or_none(s.get("brew_weight") or s.get("shotWeight")),
                        _float_or_none(s.get("dose")) or 18.0,
                        "Imported",
                    ))
                    imported += 1
                except Exception as e:
                    errors.append(f"Shot {i}: {e}")
                    skipped += 1

    if imported > 0:
        delete_model(g.user_id)

    return jsonify({
        "imported": imported,
        "skipped":  skipped,
        "errors":   errors[:10],  # cap error list
    })


def _serialize(s: dict) -> dict:
    brew_ratio = None
    if s.get("brew_weight") and s.get("dose") and s["dose"] > 0:
        brew_ratio = round(s["brew_weight"] / s["dose"], 2)
    return {
        "id":              str(s["id"]),
        "grind_size":      s["grind_size"],
        "extraction_time": s["extraction_time"],
        "brew_weight":     s.get("brew_weight"),
        "dose":            s.get("dose"),
        "brew_ratio":      brew_ratio,
        "rating":          s.get("rating"),
        "notes":           s.get("notes"),
        "bean_id":         str(s["bean_id"]) if s.get("bean_id") else None,
        "bean_name":       s.get("bean_name"),
        "roast":           s.get("roast"),
        "created_at":      s["created_at"].isoformat() if s.get("created_at") else None,
    }


def _float_or_none(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None
