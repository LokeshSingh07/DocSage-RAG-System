from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException

from app.repository.auth_query import (
    get_user_by_email,
    get_default_user,
)


@dataclass
class Principal:
    tenant: str
    owner: str
    groups: list[str]
    user_id: UUID | None = None
    email: str | None = None
    full_name: str | None = None


def get_principal(
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> Principal:
    """
    FastAPI dependency that fetches user information from the database and constructs a Principal.

    - If 'X-User-Email' is provided, fetches the user by email.
    - If 'X-User-Id' is provided, fetches the user by UUID.
    - If neither is provided, falls back to the default/primary user in the database (useful for local dev and testing).
    - If no matching user is found, raises HTTPException(401).
    """
    user = None

    if x_user_email is not None:
        user = get_user_by_email(x_user_email)
        if not user:
            raise HTTPException(status_code=401, detail=f"User with email '{x_user_email}' not found")
    else:
        user = get_default_user()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="No user found in database. Please register/create a user first.",
            )

    return Principal(
        tenant="default",
        owner=user["email"],
        groups=["user"],
        user_id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
    )
