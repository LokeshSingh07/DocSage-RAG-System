import logging
from app.core.config import get_settings as settings
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


logger = logging.getLogger(__name__)

_pool = None


def get_db() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings().database_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=True
        )
    return _pool


def close_db():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def check_db_connection():
    try:
        with get_db().connection() as conn:
            conn.execute("SELECT 1")
        return True

    except Exception as e:
        logger.warning(f"DB connection check failed: {e}")
        return False