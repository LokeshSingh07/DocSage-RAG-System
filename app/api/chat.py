from fastapi import APIRouter, Depends, Response
from app.graph import chat as graph_chat
from app.core.security import get_principal, Principal

router = APIRouter()


@router.get("/ask")
def get_answer(question: str = "What is Pinecone?", principal: Principal = Depends(get_principal)):
    try:
        result = graph_chat(principal, question)
        return {
            "question": question,
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

