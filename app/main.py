from fastapi import FastAPI
from app.core.db import engine, Base
from app.core.observability import initialize
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router


app = FastAPI(
    title="RAG System",
    description="RAG System Backend API",
    version="1.0.0"
)
Base.metadata.create_all(bind=engine)

initialize()



# ================== API ROUTES ==================
app.include_router(
    documents_router,
    prefix="/api/v1/document",
    tags=["Documents"]
)

app.include_router(
    chat_router,
    prefix="/api/v1/chat",
    tags=["Chat"]
)









# ================== DEFAULT ROUTES ==================
@app.get("/")
async def root():
    return {"message": f"Server is up and running..."}



@app.get("/health")
async def health():
    return {"status": "OK"}
