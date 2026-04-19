"""
db.py – Neon (PostgreSQL) connection management
Compatible with Render + Neon serverless setup
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")


@contextmanager
def get_db():
    """Open connection per request (serverless-safe)"""
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Idempotent schema creation + lightweight migrations for Neon PostgreSQL."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email           TEXT UNIQUE NOT NULL,
                    password_hash   TEXT NOT NULL,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS beans (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name        TEXT NOT NULL,
                    roast       TEXT CHECK (roast IN ('light','medium','dark')) DEFAULT 'medium',
                    origin      TEXT,
                    roastery    TEXT,
                    bean_type   TEXT DEFAULT 'arabica',
                    created_at  TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS shots (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    bean_id         UUID REFERENCES beans(id) ON DELETE SET NULL,
                    grind_size      REAL,
                    extraction_time REAL NOT NULL,
                    brew_weight     REAL,
                    dose            REAL DEFAULT 18.0,
                    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),
                    notes           TEXT,
                    source          TEXT DEFAULT 'manual',
                    profile_name    TEXT,
                    peak_pressure   REAL,
                    raw_data        JSONB,
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS user_models (
                    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    model_blob  TEXT NOT NULL,
                    n_samples   INTEGER DEFAULT 0,
                    r2_score    REAL,
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            migrations = [
                "ALTER TABLE beans ADD COLUMN IF NOT EXISTS roastery TEXT",
                "ALTER TABLE beans ADD COLUMN IF NOT EXISTS bean_type TEXT",
                "ALTER TABLE beans ALTER COLUMN bean_type SET DEFAULT 'arabica'",
                "UPDATE beans SET bean_type = 'arabica' WHERE bean_type IS NULL",
                "ALTER TABLE shots ALTER COLUMN grind_size DROP NOT NULL",
                "ALTER TABLE shots ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual'",
                "ALTER TABLE shots ADD COLUMN IF NOT EXISTS profile_name TEXT",
                "ALTER TABLE shots ADD COLUMN IF NOT EXISTS peak_pressure REAL",
                "ALTER TABLE shots ADD COLUMN IF NOT EXISTS raw_data JSONB",
                "UPDATE shots SET source = 'manual' WHERE source IS NULL",
            ]
            for stmt in migrations:
                cur.execute(stmt)

            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'beans_bean_type_check'
                    ) THEN
                        ALTER TABLE beans
                        ADD CONSTRAINT beans_bean_type_check
                        CHECK (bean_type IN ('arabica','robusta','blend'));
                    END IF;
                END $$;
            """)

    print("[DB] Schema initialized successfully.")
