from uuid import UUID
from app.core.db import get_db 

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from psycopg.errors import UniqueViolation

ph = PasswordHasher()


# create user entry
def create_user(full_name: str, email: str, password: str) -> dict:
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
                    (full_name, email, hashed_password)
                )
                return cur.fetchone()
    except UniqueViolation:
        raise ValueError("Email already registered")


# login user
def login_user(email: str, password: str) -> dict | None:
    # check user exist
    user = get_user_by_email(email)
    if not user:
        return None
    
    try:
        ph.verify(user["password_hash"], password)
    except VerifyMismatchError:
        return None
    user.pop("password_hash")
    return user


# get user by email
def get_user_by_email(email: str) -> dict | None:
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,),
        ).fetchone()


# get user by id
def get_user_by_id(user_id: UUID) -> dict | None:
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT id, full_name, email, created_at FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()


# get default user (first registered user in DB)
def get_default_user() -> dict | None:
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT id, full_name, email, created_at FROM users ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
