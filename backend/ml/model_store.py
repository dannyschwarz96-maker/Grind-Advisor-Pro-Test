"""
ml/model_store.py – Serialize/deserialize UserGrindModel to/from Neon DB

Why DB instead of filesystem?
  Render Free Tier has ephemeral disk → files lost on each deploy/restart.
  Neon is the only persistent storage we have → model blob goes there.
"""

import base64
import pickle

from db import get_db
from ml.model import UserGrindModel


def save_model(user_id: str, model: UserGrindModel) -> None:
    """Pickle + base64 encode the model, upsert into user_models."""
    blob = base64.b64encode(pickle.dumps(model)).decode("ascii")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_models (user_id, model_blob, n_samples, r2_score, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    model_blob  = EXCLUDED.model_blob,
                    n_samples   = EXCLUDED.n_samples,
                    r2_score    = EXCLUDED.r2_score,
                    updated_at  = NOW()
            """, (user_id, blob, model.n_samples, model.r2))


def load_model(user_id: str) -> UserGrindModel | None:
    """Load and deserialize model for a user. Returns None if not found."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT model_blob FROM user_models WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
    if not row:
        return None
    try:
        return pickle.loads(base64.b64decode(row["model_blob"]))
    except Exception:
        # Corrupt blob → delete and retrain
        delete_model(user_id)
        return None


def delete_model(user_id: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_models WHERE user_id = %s", (user_id,))


def get_model_meta(user_id: str) -> dict | None:
    """Return model metadata without loading the full blob."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT n_samples, r2_score, updated_at
                FROM user_models WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
    if not row:
        return None
    return {
        "n_samples": row["n_samples"],
        "r2_score": row["r2_score"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def get_current_shot_count(user_id: str) -> int:
    """Used to detect if model needs retraining (new shots added since last train)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as n FROM shots WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
    return row["n"] if row else 0
