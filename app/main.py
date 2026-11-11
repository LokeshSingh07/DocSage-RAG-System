from contextlib import asynccontextmanager
from pathlib import Path
import threading
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.core.db import engine, Base
from app.core.observability import initialize
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _warmup_clients():
    """Pre-build the Bedrock client and Pinecone index so the first request is fast."""
    try:
        from app.core.aws import client
        from app.vector_pinecone import index

        client("bedrock-runtime")
        index()
        logger.info("Warmup complete")
    except Exception:
        # warning level so a bad key or unreachable service shows up at startup
        logger.warning("Warmup failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    Base.metadata.create_all(bind=engine)
    initialize()
    threading.Thread(target=_warmup_clients, daemon=True).start()

    yield

    # ---- shutdown ----
    engine.dispose()


app = FastAPI(
    title="RAG System",
    description="RAG System Backend API",
    version="1.0.0",
    lifespan=lifespan,
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
async def root(request: Request):
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request=request, name="index.html")
    return JSONResponse({"message": "Server is up and running..."})


@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")



@app.get("/health")
async def health():
    return {"status": "OK"}
