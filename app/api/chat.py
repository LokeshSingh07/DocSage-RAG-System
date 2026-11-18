from uuid import UUID
import logging
from fastapi import APIRouter, Depends, Query, HTTPException

from app.graph import chat as graph_chat
from app.core.security import get_principal, Principal
from app.repository.chat_query import (
    get_or_create_conversation,
    get_recent_messages,
    format_history_for_llm,
    create_message,
    get_conversation_by_id,
    list_conversations_by_user,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ask")
def get_answer(
    question: str = "What is Pinecone?",
    conversation_id: UUID | None = Query(default=None, description="Optional existing conversation UUID"),
    document_id: UUID | None = Query(default=None, description="Optional document UUID to associate"),
    principal: Principal = Depends(get_principal),
):
    try:
        # 1. Get or create a conversation for this user
        conversation = get_or_create_conversation(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            title=question[:80] if len(question) > 80 else question,
            document_id=document_id,
        )
        conv_id = conversation["id"]

        # 2. Retrieve recent message history and format for the LLM
        recent_db_messages = get_recent_messages(conv_id, limit=10)
        history = format_history_for_llm(recent_db_messages)

        # 3. Store user message in database
        create_message(
            conversation_id=conv_id,
            role="user",
            content=question,
        )

        # 4. Run LangGraph RAG pipeline with history
        result = graph_chat(principal, question, history)

        # 5. Store assistant response with sources in database
        create_message(
            conversation_id=conv_id,
            role="assistant",
            content=result.get("answer", ""),
            sources=result.get("sources"),
        )

        return {
            "question": question,
            "conversation_id": str(conv_id),
            "status": "success",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@router.get("/history/{conversation_id}")
def get_conversation_history(
    conversation_id: UUID,
    principal: Principal = Depends(get_principal),
):
    """Fetch message history for a given conversation."""
    conv = get_conversation_by_id(conversation_id)
    if not conv or str(conv["user_id"]) != str(principal.user_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = get_recent_messages(conversation_id, limit=50)
    return {
        "conversation_id": str(conversation_id),
        "title": conv["title"],
        "messages": messages,
    }


@router.get("/conversations")
def list_conversations(principal: Principal = Depends(get_principal)):
    """Fetch all conversations belonging to the authenticated user."""
    return list_conversations_by_user(principal.user_id)
