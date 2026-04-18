"""
db.py – Neon (PostgreSQL) connection management
Uses a connection-per-request pattern suitable for Render Free Tier
(no persistent connection pool; Neon handles serverless well)
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")


@contextmanager
def get_db():
    """Context manager: opens a connection, commits or rolls back, then closes."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Create all tables if they don't exist.
    Called once on app startup (safe to run repeatedly – idempotent).
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                -- Users table
                CREATE TABLE IF NOT EXISTS users (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email       TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );

                -- Beans table
                CREATE TABLE IF NOT EXISTS beans (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name        TEXT NOT NULL,
                    roast       TEXT CHECK (roast IN ('light', 'medium', 'dark')) DEFAULT 'medium',
                    origin      TEXT,
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );

                -- Shots table (central data for ML)
                CREATE TABLE IF NOT EXISTS shots (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    bean_id         UUID REFERENCES beans(id) ON DELETE SET NULL,
                    grind_size      REAL NOT NULL,
                    extraction_time REAL NOT NULL,
                    brew_weight     REAL,
                    dose            REAL DEFAULT 18.0,
                    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
                    notes           TEXT,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                );

                -- Serialized per-user ML models (blob stored in DB → survives Render restarts)
                CREATE TABLE IF NOT EXISTS user_models (
                    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    model_blob  TEXT NOT NULL,
                    n_samples   INTEGER NOT NULL DEFAULT 0,
                    r2_score    REAL,
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                );
            """)
    print("[DB] Schema initialized.")
