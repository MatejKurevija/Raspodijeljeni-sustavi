# db.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Čita konekcijski string iz varijable okoline DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    Kreira tablice ako ne postoje, i dodaje last_active u worker_status.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        type VARCHAR NOT NULL,
        parameters TEXT NOT NULL,
        status VARCHAR NOT NULL,
        worker_id VARCHAR,
        result TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS worker_status (
        id SERIAL PRIMARY KEY,
        worker_id VARCHAR UNIQUE NOT NULL,
        status VARCHAR NOT NULL,
        last_seen TIMESTAMPTZ NOT NULL,
        last_active TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS leader_status (
        leader_id VARCHAR PRIMARY KEY,
        last_seen TIMESTAMPTZ NOT NULL
    );
    """
    alter = """
    ALTER TABLE worker_status
      ADD COLUMN IF NOT EXISTS last_active TIMESTAMPTZ NOT NULL DEFAULT now();
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(alter)
        conn.commit()
