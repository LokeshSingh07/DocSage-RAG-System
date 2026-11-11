from app.vector_pinecone import search



def retriever(tenant: str, query: str, groups: list[str], owner: str, limit: int = 8):
    search_results = search(tenant, query, groups, owner, limit)
    return search_results