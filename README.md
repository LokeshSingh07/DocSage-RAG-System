# DocSage Enterprise RAG System

An enterprise-grade Retrieval-Augmented Generation (RAG) backend and web interface built with **FastAPI**, **LangGraph**, **PostgreSQL** (`psycopg-pool`), **Celery + Redis**, **Pinecone**, and **AWS Bedrock / S3**.

Features asynchronous document ingestion, multi-tenant Pinecone namespace isolation, multi-turn conversational memory, role-based access filtering, input/output guardrails, and Rius observability.

---

## Architecture Overview

### 1. Document Ingestion Flow (Async with Celery & S3)
```mermaid
flowchart LR
    Client([Client]) -->|POST /api/v1/document| API[FastAPI Upload Endpoint]
    API -->|1. Store record| DB[(PostgreSQL)]
    API -->|2. Upload raw file| S3[(AWS S3)]
    API -->|3. ingest_task.delay| Redis[(Redis Broker)]
    Redis --> Worker[Celery Worker]
    Worker -->|download_from_s3| S3
    Worker -->|PyPDFLoader / TextLoader\n+ RecursiveCharacterTextSplitter| Chunks[Text Chunks]
    Worker -->|Bedrock Titan Embed| Embeddings[1024-dim Vectors]
    Worker -->|Upsert + Metadata| Pinecone[(Pinecone Serverless)]
    Worker -->|Update status: ready| DB
```

### 2. Query & Multi-Turn Chat Flow (LangGraph)
```mermaid
flowchart TD
    User(["GET /api/v1/chat/ask"]) --> API[FastAPI Chat Endpoint]
    API -->|Load last 10 turns| DB[(PostgreSQL)]
    API --> Guard["1. guard\n(check_input: injection, length, unicode)"]
    Guard -- GuardrailError --> Blocked["Return status: 'blocked'"] --> END([END])
    Guard -- Clean --> Retrieve["2. retrieve\n(Pinecone search: tenant, owner/groups, score)"]

    Retrieve --> Check{"Passages or\nHistory Exist?"}
    Check -- No Passages & No History --> NoAnswer["3b. no_answer\n(Return fallback message)"] --> END
    Check -- Passages or History Found --> Generate["3a. generate\n(ask_llm -> Bedrock Converse + history + check_output)"]
    Generate --> Save["4. Store user & assistant messages"] --> DB
    Save --> END
```

---

## Key Features

- **Multi-Turn Conversational Memory**: Conversations and messages are saved in PostgreSQL with JSONB retrieved citations. History is fed into LangGraph and the LLM for contextual follow-ups and meta-questions (e.g. *"what did we discuss earlier?"*).
- **Async Document Ingestion**: Uploads `.pdf`, `.md`, and `.txt` files (up to 5 MB) to AWS S3 and processes chunking/embedding asynchronously via Celery workers with automatic retries and live status tracking (`uploaded` $\to$ `processing` $\to$ `ready` / `failed`).
- **LangGraph State Orchestration**: Robust state graph with conditional edges in `app/graph.py` evaluating both document passages and conversation memory.
- **Multi-Tenant & Access Control**: Pinecone namespaces (`tenant-{tenant}`) with metadata filtering on `owner_sub` and `allowed_groups`, plus configurable `MIN_RELEVANCE_SCORE`.
- **AWS Bedrock & Pluggable LLM Factory**:
  - **Embeddings**: `amazon.titan-embed-text-v2:0` (1024 dimensions)
  - **Chat LLM**: `amazon.nova-micro-v1:0` via AWS Bedrock Converse API (extensible via `app/llm/factory.py`)
- **Native PostgreSQL Storage**: High-performance connection pooling via `psycopg-pool` and raw SQL queries organized in the repository pattern.
- **Input & Output Guardrails**: Blocks prompt injection/jailbreak attempts and automatically redacts leaked secrets (AWS keys, JWTs, DB URLs, Bearer tokens, API keys).
- **ChatGPT / Claude Style Web UI**: Sleek sidebar layout for browsing past conversations, switching user identities, uploading files, and monitoring background ingestion tasks.
- **Observability**: Privacy-first telemetry via `glassflow-rius` (`@trace`, `initialize()`).

---

## Project Structure

```text
├── app/
│   ├── api/
│   │   ├── chat.py           # Chat endpoints (/ask, /history, /conversations)
│   │   └── documents.py      # Document upload & status (/document, /process, /my-documents)
│   ├── core/
│   │   ├── aws.py            # Boto3 client, S3 upload/download, Bedrock runtime
│   │   ├── config.py         # Pydantic Settings (.env loader)
│   │   ├── db.py             # psycopg_pool connection pool & health check
│   │   ├── init_db.py        # Schema initialization and advisory lock management
│   │   ├── observability.py  # Rius tracing initialization and @trace decorator
│   │   ├── schema.sql        # PostgreSQL DDL (users, documents, conversations, messages)
│   │   └── security.py       # Principal dataclass and get_principal auth dependency
│   ├── llm/
│   │   ├── bedrock.py        # AWS Bedrock Converse API integration
│   │   ├── factory.py        # Pluggable LLM provider factory
│   │   └── prompt.py         # Grounded system prompt templates
│   ├── rag/
│   │   ├── embedding.py      # Bedrock Titan embedding helper
│   │   ├── ingestion.py      # S3 download, document loaders, chunking, Pinecone upsert
│   │   └── retrieval.py      # Pinecone query & relevance filtering
│   ├── repository/
│   │   ├── auth_query.py     # User queries & Argon2id password hashing
│   │   ├── chat_query.py     # Conversation and message CRUD operations
│   │   ├── document_query.py # Document creation, status updates, and user document lists
│   │   └── queries.py        # Consolidated repository exports
│   ├── templates/
│   │   └── index.html        # ChatGPT / Claude style web interface
│   ├── graph.py              # LangGraph StateGraph & chat() entrypoint
│   ├── guardrails.py         # check_input & check_output guardrails
│   ├── main.py               # FastAPI application setup, routes & lifespan
│   └── vector_pinecone.py    # Pinecone client, namespace isolation, upsert & search
├── worker/
│   ├── celery_app.py         # Celery application configuration (Redis broker/backend)
│   └── tasks.py              # Async ingest_task worker task
├── Dockerfile                # Production multi-stage Docker build
├── docker-compose.yml        # Orchestration for API, Celery Worker, and Redis
├── requirements.txt          # Python dependencies
└── README.md
```

---

## Getting Started

### 1. Prerequisites

- **Python 3.12+**
- **PostgreSQL 13+** (local or hosted e.g. Neon, Supabase, Prisma Postgres)
- **Redis 7+** (for Celery broker and result backend)
- **AWS Account** with an S3 bucket and Bedrock model access:
  - `amazon.titan-embed-text-v2:0`
  - `amazon.nova-micro-v1:0`
- **Pinecone** account and API key

### 2. Installation

1. **Clone the repository and set up a virtual environment:**
   ```bash
   git clone <repo-url>
   cd RAG_system
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. Environment Variables

Create a `.env` file in the project root:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET_NAME=your_s3_bucket_name
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_CHAT_MODEL=amazon.nova-micro-v1:0
EMBED_DIM=1024
EMBED_NORMALIZE=True

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_READY_TIMEOUT=180

# Retrieval & LLM Settings
LLM_PROVIDER=bedrock
MIN_RELEVANCE_SCORE=0.3

# PostgreSQL & Redis Configuration
DATABASE_URL=postgres://user:password@localhost:5432/dbname?sslmode=require
REDIS_URL=redis://localhost:6379

# Observability (Optional)
RIUS_API_KEY=
RIUS_SERVICE_NAME=rag-system
RIUS_DISABLED=True
RIUS_CAPTURE_CONTENT=False
```

### 4. Database Setup

Initialize and verify the PostgreSQL schema (tables: `users`, `documents`, `conversations`, `messages`):

```bash
python -m app.core.init_db
```

---

## Running the Application

### Option A: Running Locally

1. **Start Redis:**
   ```bash
   redis-server
   ```

2. **Start the Celery Worker** (in a separate terminal):
   ```bash
   celery -A worker.celery_app worker --loglevel=info
   ```

3. **Start the FastAPI Server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Option B: Running with Docker Compose

Run all services (API, Celery worker, and Redis) simultaneously:

```bash
docker compose up --build
```

---

## Web Interface & API Documentation

- **Web UI**: Navigate to `http://localhost:8000/` or `http://localhost:8000/ui` in your browser.
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## API Endpoints

### Documents

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/document` | Upload `.pdf`, `.md`, or `.txt` to S3 and queue Celery ingestion |
| `POST` | `/api/v1/document/process/{task_id}` | Check Celery ingestion task status and result |
| `GET` | `/api/v1/document/my-documents` | List all uploaded documents and live DB status for current user |
| `GET` | `/api/v1/document/status/{document_id}` | Fetch document details by UUID |

### Chat & Conversations

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/chat/ask` | Query the RAG pipeline (`?question=...&conversation_id=...`) |
| `GET` | `/api/v1/chat/history/{conversation_id}` | Fetch previous message history for a conversation |
| `GET` | `/api/v1/chat/conversations` | List all past conversation threads for the user |

### Health Check

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Check PostgreSQL connection and Bedrock/Pinecone warmup status |

---

## Example Usage

### 1. Upload a Document
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/document" \
     -H "X-User-Email: user@example.com" \
     -F "file=@sample_test.txt"
```

### 2. Check Ingestion Task Status
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/document/process/<task_id>"
```

### 3. Ask a Question (with Conversational Memory)
```bash
# First question (creates a conversation)
curl -X GET "http://127.0.0.1:8000/api/v1/chat/ask?question=What+is+Pinecone%3F" \
     -H "X-User-Email: user@example.com"

# Follow-up question in the same conversation
curl -X GET "http://127.0.0.1:8000/api/v1/chat/ask?question=What+was+my+previous+question%3F&conversation_id=<conversation_id>" \
     -H "X-User-Email: user@example.com"
```

### 4. Fetch Conversation History
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/chat/history/<conversation_id>" \
     -H "X-User-Email: user@example.com"
```
