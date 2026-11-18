from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.core.aws import upload_to_S3
import uuid
from uuid import UUID
from app.core.security import get_principal, Principal
from worker.tasks import ingest_task
from app.repository.document_query import (
    create_document,
    get_document_by_id,
    list_documents_by_user,
)

router = APIRouter()


ALLOWED = ["pdf", "md", "txt"]
MAX_BYTES = 5 * 1024 * 1024




# =============================================================
# Document Upload & Ingest
# =============================================================
@router.post("", status_code=201)
def upload_document(file: UploadFile = File(...), principal: Principal = Depends(get_principal)):
    try:
        # check file size and extension
        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED:
            raise HTTPException(status_code=400, detail="Invalid file extension")
            
        file_bytes = file.file.read()
        file_size = len(file_bytes)
        if file_size > MAX_BYTES:
            raise HTTPException(status_code=413, detail="File size is too large")

        result = upload_to_S3(file_bytes, file.filename)

        # store the document detail in db
        doc = create_document(
            user_id=principal.user_id,
            file_name=file.filename,
            file_size=file_size,
            s3_key=result["key"],
            file_type=file.content_type or ext,
        )

        # ingest run in bg
        doc_id = str(doc["id"])
        task = ingest_task.delay(result["key"], principal.tenant, doc_id, principal.owner, principal.groups)

        return {
            "status": "queued",
            "message": "File uploaded successfully",
            "task_id": task.id,
            "document_id": doc_id,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# =============================================================
# RAG Ingestion Status
# =============================================================
@router.get("/process/{task_id}")
def document_status(task_id: str):
    try:
        result = ingest_task.AsyncResult(task_id)
        
        return {
            "state": result.state,   # PENDING / STARTED / RETRY / SUCCESS / FAILURE
            "result": result.result if result.successful() else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-documents")
def get_user_documents(principal: Principal = Depends(get_principal)):
    """List all documents uploaded by the current user."""
    return list_documents_by_user(principal.user_id)


@router.get("/status/{document_id}")
def get_document_status(document_id: UUID, principal: Principal = Depends(get_principal)):
    """Get the current DB status of an uploaded document."""
    doc = get_document_by_id(document_id)
    if not doc or str(doc["user_id"]) != str(principal.user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc