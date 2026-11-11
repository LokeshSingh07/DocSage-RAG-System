from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from app.core.aws import upload_to_S3
import uuid
from app.core.security import get_principal, Principal
from worker.tasks import ingest_task

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
        ext = file.filename.split(".")[-1]
        if ext not in ALLOWED:
            raise HTTPException(status_code=400, detail="Invalid file extension")
            
        if file.size is None or file.size > MAX_BYTES:
            raise HTTPException(status_code=413, detail="File size is too large")


        result = upload_to_S3(file.file.read(), file.filename)

        # ingest run in bg
        task = ingest_task.delay(result["key"], principal.tenant, uuid.uuid4().hex[:7], principal.owner, principal.groups)

        return {
            "status": "queued",
            "message": "File uploaded successfully",
            "task_id": task.id,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# =============================================================
# RAG Ingestion Status
# =============================================================
@router.post("/process/{task_id}")
def document_status(task_id: str):
    try:
        result = ingest_task.AsyncResult(task_id)
        
        return {
            "state": result.state,   # PENDING / STARTED / RETRY / SUCCESS / FAILURE
            "result": result.result if result.successful() else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))