# py -m tests.test_db

from app.core.db import get_db, close_db, check_db_connection


with get_db().connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    print("Created test_users table")


close_db()
