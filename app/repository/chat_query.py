import json
import logging
from uuid import UUID
from app.core.db import get_db

logger = logging.getLogger(__name__)


def create_conversation(
    user_id: UUID | str,
    title: str = "New Chat",
    document_id: UUID | str | None = None,
) -> dict:
    """Create a new conversation record."""
    try:
        with get_db().connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    """
                    INSERT INTO conversations (user_id, title, document_id)
                    VALUES (%s, %s, %s)
                    RETURNING id, user_id, title, document_id, created_at
                    """,
                    (user_id, title, document_id),
                )
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}", exc_info=True)
        raise ValueError(f"Failed to create conversation: {e}")


def get_conversation_by_id(conversation_id: UUID | str) -> dict | None:
    """Fetch conversation by ID."""
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT id, user_id, title, document_id, created_at FROM conversations WHERE id = %s",
            (conversation_id,),
        ).fetchone()


def get_latest_conversation(user_id: UUID | str) -> dict | None:
    """Fetch the latest conversation for a user."""
    with get_db().connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, title, document_id, created_at 
            FROM conversations 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()


def list_conversations_by_user(user_id: UUID | str) -> list[dict]:
    """Fetch all conversations for a user ordered by newest first."""
    with get_db().connection() as conn:
        return conn.execute(
            """
            SELECT id, user_id, title, document_id, created_at 
            FROM conversations 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()


def get_or_create_conversation(
    user_id: UUID | str,
    conversation_id: UUID | str | None = None,
    title: str = "New Chat",
    document_id: UUID | str | None = None,
) -> dict:
    """
    Retrieve an existing conversation if conversation_id is provided and owned by user.
    Otherwise create a new conversation for this user.
    """
    if conversation_id:
        conv = get_conversation_by_id(conversation_id)
        if conv and str(conv["user_id"]) == str(user_id):
            return conv

    return create_conversation(user_id=user_id, title=title, document_id=document_id)


def create_message(
    conversation_id: UUID | str,
    role: str,
    content: str,
    sources: list | None = None,
) -> dict:
    """Insert a user or assistant message with optional sources."""
    try:
        sources_json = json.dumps(sources) if sources is not None else None
        with get_db().connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, sources)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id, conversation_id, role, content, sources, created_at
                    """,
                    (conversation_id, role, content, sources_json),
                )
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to create message: {e}", exc_info=True)
        raise ValueError(f"Failed to create message: {e}")


def get_recent_messages(conversation_id: UUID | str, limit: int = 10) -> list[dict]:
    """Fetch the last `limit` messages in chronological order (oldest to newest)."""
    with get_db().connection() as conn:
        return conn.execute(
            """
            SELECT id, conversation_id, role, content, sources, created_at
            FROM (
                SELECT id, conversation_id, role, content, sources, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ) sub
            ORDER BY created_at ASC
            """,
            (conversation_id, limit),
        ).fetchall()


def format_history_for_llm(messages: list[dict]) -> list[dict]:
    """Format stored DB messages into the list format expected by the LLM."""
    return [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") in ("user", "assistant")]
