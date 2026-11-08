from fastapi import APIRouter, Depends, Response

router = APIRouter()


@router.get("/")
def get_documents():
    return {"message": "API is up and running..."}