from app.core.db import get_db, close_db, check_db_connection

from argon2 import PasswordHasher
from psycopg.errors import UniqueViolation

ph = PasswordHasher()


def create_user(full_name: str, email: str, password: str):
    hashed_password = ph.hash(password)
    try:
        with get_db().connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    """
                    INSERT INTO users (full_name, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, full_name, email, created_at
                    """,
                    (full_name, email, hashed_password),
                )
                return cur.fetchone()
    except UniqueViolation:
        raise ValueError("Email already registered")


if __name__ == "__main__":
    try:
        print("DB connection ok:", check_db_connection())
        print(create_user("admin", "admin@example.com", "123456"))
    finally:
        close_db()
