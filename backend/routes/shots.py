"""
routes/shots.py – Shot CRUD + Gaggiuino JSON import
"""

from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json
from auth_utils import require_auth
from db import get_db
from ml.model_store import delete_model

shots_bp = Blueprint("shots", __name__)


@shots_bp.route("/", methods=["GET"])
@require_auth
def list_shots():
    bean_id = request.args.get("bean_id")
    limit = min(int(request.args.get("limit", 100)), 500)

    with get_db() as conn:
        with conn.cursor() as cur:
            if bean_id:
                cur.execute("""
                    SELECT s.*, b.name as bean_name, b.roast, b.roastery, b.bean_type
                    FROM shots s LEFT JOIN beans b ON b.id = s.bean_id
                    WHERE s.user_id = %s AND s.bean_id = %s
                    ORDER BY s.created_at DESC LIMIT %s
                """, (g.user_id, bean_id, limit))
            else:
                cur.execute("""
                    SELECT s.*, b.name as bean_name, b.roast, b.roastery, b.bean_type
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

    grind_size = data.get("grind_size")
    extraction_time = data.get("extraction_time")

    if grind_size is None or extraction_time is None:
        return jsonify({"error": "grind_size and extraction_time are required"}), 400
    try:
        grind_size = float(grind_size)
        extraction_time = float(extraction_time)
    except (ValueError, TypeError):
        return jsonify({"error": "grind_size and extraction_time must be numbers"}), 400

    if grind_size <= 0 or extraction_time <= 0:
        return jsonify({"error": "Values must be positive"}), 400

    brew_weight = _float_or_none(data.get("brew_weight"))
    dose = _float_or_none(data.get("dose")) or 18.0
    bean_id = data.get("bean_id") or None
    rating = data.get("rating")
    notes = (data.get("notes") or "").strip() or None

    if rating is not None:
        rating = int(rating)
        if not 1 <= rating <= 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            if bean_id:
                cur.execute("SELECT id FROM beans WHERE id = %s AND user_id = %s", (bean_id, g.user_id))
                if not cur.fetchone():
                    return jsonify({"error": "Selected bean not found"}), 404
            cur.execute("""
                INSERT INTO shots
                  (user_id, bean_id, grind_size, extraction_time, brew_weight, dose, rating, notes, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual')
                RETURNING *
            """, (g.user_id, bean_id, grind_size, extraction_time, brew_weight, dose, rating, notes))
            shot = _serialize(dict(cur.fetchone()))

    delete_model(g.user_id)
    return jsonify(shot), 201


@shots_bp.route('/<shot_id>/curve', methods=['GET'])
@require_auth
def get_shot_curve(shot_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, source, profile_name, raw_data FROM shots WHERE id = %s AND user_id = %s",
                (shot_id, g.user_id),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Shot not found"}), 404
    if row['source'] != 'gaggiuino' or not row.get('raw_data'):
        return jsonify({"error": "No curve data available for this shot"}), 404

    raw = row['raw_data']
    datapoints = raw.get('datapoints', [])
    return jsonify({
        'shot_id': str(row['id']),
        'source': row['source'],
        'profile_name': row.get('profile_name') or raw.get('profile', {}).get('name'),
        'summary': _build_gaggiuino_summary(raw, datapoints),
        'curve': _build_curve_payload(raw, datapoints),
    })


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


@shots_bp.route('/import', methods=['POST'])
@require_auth
def import_shot():
    data = request.get_json(silent=True) or {}
    validation_error = _validate_gaggiuino_export(data)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    datapoints = data['datapoints']
    summary = _build_gaggiuino_summary(data, datapoints)
    curve = _build_curve_payload(data, datapoints)
    bean_id = request.args.get('bean_id') or (data.get('bean_id')) or None
    notes = (data.get('notes') or '').strip() or 'Imported from Gaggiuino'

    with get_db() as conn:
        with conn.cursor() as cur:
            if bean_id:
                cur.execute("SELECT id FROM beans WHERE id = %s AND user_id = %s", (bean_id, g.user_id))
                if not cur.fetchone():
                    return jsonify({"error": "Selected bean not found"}), 404

            cur.execute("""
                INSERT INTO shots
                  (user_id, bean_id, grind_size, extraction_time, brew_weight, dose, rating, notes,
                   source, profile_name, peak_pressure, raw_data)
                VALUES (%s, %s, NULL, %s, %s, COALESCE(%s, 18.0), NULL, %s, 'gaggiuino', %s, %s, %s)
                RETURNING *
            """, (
                g.user_id,
                bean_id,
                summary['duration_seconds'],
                summary['final_shot_weight'],
                _float_or_none(data.get('dose')),
                notes,
                summary['profile_name'],
                summary['peak_pressure'],
                Json(data),
            ))
            shot = _serialize(dict(cur.fetchone()))

    return jsonify({
        'imported': 1,
        'skipped': 0,
        'errors': [],
        'shot': shot,
        'summary': summary,
        'curve': curve,
    })


def _validate_gaggiuino_export(data: dict) -> str | None:
    if not isinstance(data, dict):
        return 'Nur Gaggiuino-Shot-Exporte als JSON werden unterstützt.'
    required_top = ('id', 'duration', 'datapoints')
    for key in required_top:
        if key not in data:
            return 'Nur Gaggiuino-Shot-Exporte werden unterstützt.'
    datapoints = data.get('datapoints')
    if not isinstance(datapoints, list) or not datapoints:
        return 'Gaggiuino-Export enthält keine Datapoints.'
    first = datapoints[0]
    if not isinstance(first, dict) or 'timeInShot' not in first:
        return 'Ungültiger Gaggiuino-Export: timeInShot fehlt.'
    allowed_metrics = {'pressure', 'pumpFlow', 'temperature', 'shotWeight'}
    if not any(any(metric in dp for metric in allowed_metrics) for dp in datapoints):
        return 'Ungültiger Gaggiuino-Export: keine Kurvendaten gefunden.'
    return None


def _build_gaggiuino_summary(data: dict, datapoints: list[dict]) -> dict:
    final_dp = datapoints[-1]
    pressure_values = [float(dp['pressure']) for dp in datapoints if _float_or_none(dp.get('pressure')) is not None]
    final_weight = _float_or_none(final_dp.get('shotWeight'))
    if final_weight is None:
        for dp in reversed(datapoints):
            final_weight = _float_or_none(dp.get('shotWeight'))
            if final_weight is not None:
                break
    return {
        'profile_name': data.get('profile', {}).get('name') or 'Gaggiuino Import',
        'duration_ms': int(data.get('duration') or 0),
        'duration_seconds': round((float(data.get('duration') or 0)) / 1000, 1),
        'final_shot_weight': final_weight,
        'peak_pressure': round(max(pressure_values), 2) if pressure_values else None,
        'datapoint_count': len(datapoints),
    }


def _build_curve_payload(data: dict, datapoints: list[dict]) -> dict:
    def point(dp, key, fallback=None):
        value = _float_or_none(dp.get(key))
        return {'x': round(float(dp.get('timeInShot', 0)) / 1000, 2), 'y': value if value is not None else fallback}

    series_map = {
        'pressure': 'pressure',
        'targetPressure': 'targetPressure',
        'pumpFlow': 'pumpFlow',
        'targetPumpFlow': 'targetPumpFlow',
        'temperature': 'temperature',
        'targetTemperature': 'targetTemperature',
        'shotWeight': 'shotWeight',
        'weightFlow': 'weightFlow',
    }
    series = {}
    for name, src in series_map.items():
        series[name] = [point(dp, src) for dp in datapoints if dp.get('timeInShot') is not None and _float_or_none(dp.get(src)) is not None]

    return {
        'profile_name': data.get('profile', {}).get('name'),
        'series': series,
    }


def _serialize(s: dict) -> dict:
    brew_ratio = None
    if s.get('brew_weight') and s.get('dose') and s['dose'] > 0:
        brew_ratio = round(s['brew_weight'] / s['dose'], 2)
    return {
        'id': str(s['id']),
        'grind_size': s.get('grind_size'),
        'extraction_time': s['extraction_time'],
        'brew_weight': s.get('brew_weight'),
        'dose': s.get('dose'),
        'brew_ratio': brew_ratio,
        'rating': s.get('rating'),
        'notes': s.get('notes'),
        'bean_id': str(s['bean_id']) if s.get('bean_id') else None,
        'bean_name': s.get('bean_name'),
        'roast': s.get('roast'),
        'roastery': s.get('roastery'),
        'bean_type': s.get('bean_type'),
        'source': s.get('source') or 'manual',
        'profile_name': s.get('profile_name'),
        'peak_pressure': s.get('peak_pressure'),
        'created_at': s['created_at'].isoformat() if s.get('created_at') else None,
    }


def _float_or_none(v):
    try:
        return None if v is None or v == '' else float(v)
    except Exception:
        return None
