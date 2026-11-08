# load, splits into chunks, embeds, store in pinecone

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.rag.embedding import embed
from app.vector_pinecone import upsert
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from app.core.aws import download_from_s3





def ingest(key: str, tenant: str, doc_id: str, owner: str, groups: list[str]) -> dict: 
    # 1. download from s3
    data = download_from_s3(key)

    # 2. extract text -> check he extension and load accordingly
    if key.endswith(".pdf"):
        loader = PyPDFLoader(data)
    else:
        loader = TextLoader(data)

    docs = loader.load()

    # 3. splits into chunks
    splitters = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitters.split_documents(docs)

    # 4. create embedding
    embeddings = [embed(chunk.page_content) for chunk in chunks]

    # 5. store in pinecone
    upsert(
        tenant=tenant,
        doc_id=doc_id,
        chunks=[chunk.page_content for chunk in chunks],
        groups=groups,
        owner=owner,
        filename=key
    )

    return {"doc_id": doc_id, "chunks": len(chunks)}