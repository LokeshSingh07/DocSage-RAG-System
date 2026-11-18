from uuid import UUID 
from app.core.db import get_db 
from app.repository.auth_query import (
    get_user_by_email,
    get_user_by_id,
    get_default_user,
    create_user,
    login_user,
)
from app.repository.document_query import (
    create_document,
    update_document_status,
    get_document_by_id,
    list_documents_by_user,
)
from app.repository.chat_query import (
    create_conversation,
    get_conversation_by_id,
    get_latest_conversation,
    get_or_create_conversation,
    create_message,
    get_recent_messages,
    format_history_for_llm,
)

__all__ = [
    "get_db",
    "get_user_by_email",
    "get_user_by_id",
    "get_default_user",
    "create_user",
    "login_user",
    "create_document",
    "update_document_status",
    "get_document_by_id",
    "list_documents_by_user",
    "create_conversation",
    "get_conversation_by_id",
    "get_latest_conversation",
    "get_or_create_conversation",
    "create_message",
    "get_recent_messages",
    "format_history_for_llm",
]
