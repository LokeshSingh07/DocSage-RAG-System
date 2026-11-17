from contextlib import asynccontextmanager
from pathlib import Path
import threading
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.core.observability import initialize
from app.core.db import get_db, close_db, check_db_connection
from app.core.init_db import init_db
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _warmup_clients(app: FastAPI):
    """Pre-build the Bedrock client and Pinecone index so the first request is fast."""
    try:
        from app.core.aws import client
        from app.vector_pinecone import index

        client("bedrock-runtime")
        index()
        app.state.warmup_ok = True

        logger.info("Warmup complete")
    except Exception:
        app.state.warmup_ok = False
        # warning level so a bad key or unreachable service shows up at startup
        logger.warning("Warmup failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    initialize()
    
    get_db()
    init_db()

    app.state.warmup_ok = False
    threading.Thread(target=_warmup_clients, args=(app,), daemon=True).start()

    yield

    # ---- shutdown ----
    logger.info("Shutting down...") 
    close_db()


app = FastAPI(
    title="RAG System",
    description="RAG System Backend API",
    version="1.0.0",
    lifespan=lifespan,
)




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
async def health(request: Request):
    db_ok = check_db_connection()
    warmup_ok = getattr(request.app.state, "warmup_ok", False)
    ready = db_ok and warmup_ok
    return JSONResponse(
        {
            "status": "OK" if ready else "DEGRADED",
            "database": db_ok,
            "clients": warmup_ok,
        },
        status_code=200 if ready else 503,
    )
