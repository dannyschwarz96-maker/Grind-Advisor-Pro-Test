"""
routes/recommend.py – ML recommendation endpoint

Strategy for Render Free Tier:
  - Models are stored in Neon DB as serialized blobs
  - Training is triggered on-demand when:
      a) No model exists for the user, OR
      b) Shot count has increased since last training
  - Training is cheap (linear regression on <1000 points) → ~50ms
  - Cached model is reused if shot count hasn't changed
"""

from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_db
from ml.model import UserGrindModel
from ml.model_store import (
    get_current_shot_count,
    get_model_meta,
    load_model,
    save_model,
)

recommend_bp = Blueprint("recommend", __name__)


def _get_or_train_model(user_id: str) -> tuple[UserGrindModel | None, dict]:
    """
    Load existing model from DB, or retrain from scratch if stale.
    Returns (model, training_metadata).
    """
    current_count = get_current_shot_count(user_id)
    meta = get_model_meta(user_id)

    # Check if cached model is still valid
    if meta and meta["n_samples"] == current_count:
        model = load_model(user_id)
        if model and model.is_trained:
            return model, {"source": "cache", **meta}

    # Fetch all shots for this user and retrain
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.grind_size, s.extraction_time,
                       s.brew_weight, s.dose, b.roast
                FROM shots s
                LEFT JOIN beans b ON b.id = s.bean_id
                WHERE s.user_id = %s
                ORDER BY s.created_at ASC
            """, (user_id,))
            shots = [dict(r) for r in cur.fetchall()]

    model = UserGrindModel(user_id)
    train_result = model.train(shots)

    if train_result.get("trained"):
        save_model(user_id, model)
        return model, {"source": "retrained", **train_result}

    return None, train_result  # Not enough data


@recommend_bp.route("/recommend", methods=["POST"])
@require_auth
def recommend():
    data = request.get_json(silent=True) or {}

    target_time  = float(data.get("target_time", 27))
    brew_weight  = float(data.get("brew_weight", 36))
    dose         = float(data.get("dose", 18))
    roast        = data.get("roast", "medium")

    model, meta = _get_or_train_model(g.user_id)

    if not model:
        return jsonify({
            "error":         "insufficient_data",
            "training_meta": meta,
            "message":       meta.get("message", ""),
        }), 422

    prediction = model.predict_optimal_grind(target_time, brew_weight, dose, roast)
    return jsonify({**prediction, "training_meta": meta})


@recommend_bp.route("/recommend/chart-data", methods=["GET"])
@require_auth
def chart_data():
    """
    Return regression line + raw shot data for the frontend chart.
    Useful for rendering without re-fetching all shots.
    """
    brew_weight = float(request.args.get("brew_weight", 36))
    dose        = float(request.args.get("dose", 18))
    roast       = request.args.get("roast", "medium")

    model, meta = _get_or_train_model(g.user_id)

    regression_line = model.get_regression_line(brew_weight, dose, roast) if model else []

    return jsonify({
        "regression_line": regression_line,
        "is_trained":      model is not None and model.is_trained,
        "training_meta":   meta,
    })


@recommend_bp.route("/recommend/model-status", methods=["GET"])
@require_auth
def model_status():
    """Quick status check – no training triggered."""
    meta = get_model_meta(g.user_id)
    current_count = get_current_shot_count(g.user_id)
    return jsonify({
        "has_model":    meta is not None,
        "is_stale":     meta is None or meta["n_samples"] != current_count,
        "current_shots": current_count,
        **(meta or {}),
    })
