from fastapi import APIRouter, Depends, Response
from dataclasses import dataclass, field
from app.graph import chat as graph_chat
from app.vector_pinecone import upsert


router = APIRouter()


@dataclass
class Principal:
    tenant: str = "test-tenant"
    owner: str = "test-user-001"
    groups: list = field(default_factory=lambda: ["engineering"])


# 1. Test Upload API: reads large txt file, chunks it, and upserts to Pinecone
@router.post("/test-upload")
def test_upload(file_path: str = "sample_test.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split text into simple 500-character chunks
        chunks = [text[i:i + 500] for i in range(0, len(text), 450)]

        upsert(
            tenant="test-tenant",
            doc_id="test-doc-001",
            chunks=chunks,
            groups=["engineering"],
            owner="test-user-001",
            filename=file_path
        )

        return {
            "status": "success",
            "file": file_path,
            "chunks_uploaded": len(chunks)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# 2. Test Query API: tests the full graph flow
@router.get("/test-query")
def test_query(question: str = "What is Pinecone?"):
    try:
        p = Principal()
        result = graph_chat(p, question)
        return {
            "question": question,
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

