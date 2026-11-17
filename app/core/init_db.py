import logging
from pathlib import Path
from app.core.db import get_db, close_db

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_LOCK_ID = 727001


def init_db():
    """Create extensions, types, tables and indexes if they don't exist."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_db().connection() as conn:
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK_ID,))
            conn.execute(sql)

    logger.info("DB schema initialized successfully")


def verify_tables() -> list[str]:
    """Return all public tables currently in the connected database."""
    with get_db().connection() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        ).fetchall()
        return [r["table_name"] for r in rows]

