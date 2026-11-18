import logging
from uuid import UUID
from app.core.db import get_db

logger = logging.getLogger(__name__)


def create_document(
    user_id: UUID | str,
    file_name: str,
    file_size: int,
    s3_key: str,
    file_type: str | None = None,
    status: str = "uploaded",
) -> dict:
    """Create a new document entry in PostgreSQL."""
    if not file_type:
        file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown"

    try:
        with get_db().connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    """
                    INSERT INTO documents (user_id, file_name, file_size, file_type, s3_key, status) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, file_name, file_size, file_type, s3_key, status, created_at  
                    """,
                    (user_id, file_name, file_size, file_type, s3_key, status),
                )
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to create document: {e}", exc_info=True)
        raise ValueError(f"Failed to create document: {e}")


def update_document_status(
    doc_id: UUID | str,
    status: str = "processing",
    error_message: str | None = None,
) -> dict | None:
    """Update status, error_message and processed_at timestamp of a document."""
    try:
        with get_db().connection() as conn:
            with conn.transaction():
                cur = conn.execute(
                    """
                    UPDATE documents 
                    SET status = %s, error_message = %s, processed_at = NOW() 
                    WHERE id = %s 
                    RETURNING id, user_id, file_name, status, error_message, processed_at
                    """,
                    (status, error_message, doc_id),
                )
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to update document status: {e}", exc_info=True)
        raise ValueError(f"Failed to update document status: {e}")


def get_document_by_id(doc_id: UUID | str) -> dict | None:
    """Fetch a document by its primary key UUID."""
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE id = %s",
            (doc_id,),
        ).fetchone()


def list_documents_by_user(user_id: UUID | str) -> list[dict]:
    """Fetch all documents belonging to a user ordered by newest first."""
    with get_db().connection() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
