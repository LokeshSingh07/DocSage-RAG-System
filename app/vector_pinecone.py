import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.core.config import get_settings as settings
from pinecone import Pinecone, ServerlessSpec
from app.rag.embedding import embed
from app.core.observability import trace

log = logging.getLogger(__name__)

# Pinecone singleton
@lru_cache(maxsize=1)
def index():
    s=settings()
    if not s.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is missing from .env")
    if not s.pinecone_index_name:
        raise RuntimeError("PINECONE_INDEX_NAME is missing from .env")

    pc = Pinecone(api_key=s.pinecone_api_key)
    name = s.pinecone_index_name


    # 1. Check whether the index exists; create it if not
    if name not in pc.list_indexes().names():
        log.info("Creating Pinecone index %s (dimension=%d, metric=cosine)", name, s.embed_dim)
        try:
            pc.create_index(
                name=name,
                dimension=s.embed_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud=s.pinecone_cloud, region=s.pinecone_region),
            )
        except Exception as exc:
            # Another process may have created it at the same moment (409 = already exists)
            if getattr(exc, "status", None) != 409:
                raise

    # 2. Make sure an existing index matches your embedding settings
    info = pc.describe_index(name)
    if int(info.dimension) != s.embed_dim:
        raise ValueError(
            f"Index {name} has dimension {info.dimension}, expected {s.embed_dim}. "
            "Use a different index name or fix EMBED_DIM."
        )

    # 3. Wait until the index is ready
    deadline = time.monotonic() + s.pinecone_ready_timeout
    while not pc.describe_index(name).status["ready"]:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Index {name} not ready within {s.pinecone_ready_timeout}s")
        time.sleep(3)

    return pc.Index(name)


def namespace(tenant):
    return f"tenant-{tenant}"



# Upsert chunks into Pinecone
@trace("pinecone_upsert")
def upsert(
        tenant: str, 
        doc_id: str, 
        chunks: list[str], 
        groups: list[str], 
        owner: str,
        filename="",
        batch_size: int = 100,
        embed_workers: int = 8,
        upload_workers: int = 4,
    ):

    # 1. Embed in parallel (pool.map keeps the same order as chunks)
    with ThreadPoolExecutor(max_workers=min(embed_workers, len(chunks))) as pool:
        vectors = list(pool.map(embed, chunks))

    records = [
        {
            "id": f"{doc_id}#{i}",
            "values": vec,
            "metadata": {
                "doc_id": doc_id,
                "text": chunk,
                "allowed_groups": groups,
                "owner_sub": owner,
            },
        }
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]

    # 2. Upload batches of 100, a few at a time
    ns = namespace(tenant)
    idx = index()
    batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]

    def upload(batch):
        idx.upsert(vectors=batch, namespace=ns)

    with ThreadPoolExecutor(max_workers=min(upload_workers, len(batches))) as pool:
        list(pool.map(upload, batches))

    return len(records)


# Search chunks in Pinecone
@trace("pinecone_search")
def search(tenant: str, query: str, groups: list[str], owner: str, limit: int = 5):
    clauses = [{"owner_sub": {"$eq": owner}}]
    if groups:
        clauses.append({"allowed_groups": {"$in": groups}})

    query_vector = embed(query)

    result = index().query(
        vector=query_vector,
        top_k=limit,
        namespace=namespace(tenant),
        filter={"$or": clauses},
        include_metadata=True,
    )

    min_relevance_score = settings().min_relevance_score

    # return [m.metadata["text"] for m in result.matches if m.score > min_relevance_score]
    
    seen = set()
    passages = []
    for m in result.matches:
        if m.score >= min_relevance_score:
            text = m.metadata.get("text", "")
            if text and text not in seen:
                seen.add(text)
                passages.append(text)
    return passages



# Delete (all chunks of a document, however many)
@trace("pinecone_delete")
def delete(tenant: str, doc_id: str):
    idx, ns = index(), namespace(tenant)
    deleted = 0

    # list() pages through every ID that starts with "<doc_id>#"
    for ids in idx.list(prefix=f"{doc_id}#", namespace=ns):
        ids = list(ids)
        for i in range(0, len(ids), 1000):          # Pinecone allows 1000 IDs per delete
            idx.delete(ids=ids[i:i + 1000], namespace=ns)
        deleted += len(ids)
    return deleted