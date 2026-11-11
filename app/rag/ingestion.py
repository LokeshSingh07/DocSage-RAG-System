# load, splits into chunks, embeds, store in pinecone
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.vector_pinecone import upsert
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from app.core.aws import download_from_s3
from app.core.observability import trace

import os
from pathlib import Path
import uuid
from rich import print

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path("downloads")


@trace("_load_docs")
def _load_docs(key, data):
    ext = key.split(".")[-1]

    # make sure folder exist
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_path = DOWNLOAD_DIR / f"{uuid.uuid4()}.{ext}"

    # file_path.write_bytes(data)

    # save it to disk
    with open(file_path, "wb") as f:
        f.write(data)

    try:
        if ext == "pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        return loader.load()
    except Exception as e:
        logger.error("Failed to load %s: %s", key, e)
        return []
    finally:
        file_path.unlink(missing_ok=True)
    

@trace("ingest")
def ingest(key: str, tenant: str, doc_id: str, owner: str, groups: list[str]) -> dict:
    logger.info("Ingesting %s (doc_id=%s)", key, doc_id)

    # 1. download from s3
    data = download_from_s3(key)

    # 2. extract text -> check he extension and load accordingly, pdf -> PyPDFLoader, txt -> TextLoader, but it take path so we need to save it first
    docs = _load_docs(key, data)

    # 3. splits into chunks
    splitters = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitters.split_documents(docs)

    # print("chunks", chunks)

    # 4. store in pinecone
    upsert(
        tenant=tenant,
        doc_id=doc_id,
        chunks=[chunk.page_content for chunk in chunks],
        groups=groups,
        owner=owner,
        filename=key
    )

    return {"doc_id": doc_id, "chunks": len(chunks)}