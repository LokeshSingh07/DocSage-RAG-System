-- Simple RAG schema: users, documents, conversations, messages (PostgreSQL 13+)
-- PDF text chunks + embeddings live in Pinecone, not here.


CREATE EXTENSION IF NOT EXISTS citext;

DO $$ BEGIN
    CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'ready', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE message_role AS ENUM ('user', 'assistant');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;



-- user
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(255) NOT NULL,
    email           CITEXT NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- document
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name       VARCHAR(255) NOT NULL,
    file_size       BIGINT NOT NULL CHECK (file_size >= 0),
    file_type       VARCHAR(255) NOT NULL,
    s3_key          VARCHAR(255) NOT NULL,
    -- page_count      INT NOT NULL CHECK (page_count >= 0),
    -- chunks_count    INT NOT NULL DEFAULT 0 CHECK (chunks_count >= 0),
    status          document_status NOT NULL DEFAULT 'uploaded',
    error_message   TEXT,
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);




-- conversation
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(255) NOT NULL,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- messages
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            message_role NOT NULL,
    content         TEXT NOT NULL,
    sources         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);





CREATE INDEX IF NOT EXISTS ix_documents_user        ON documents (user_id);
CREATE INDEX IF NOT EXISTS ix_conversations_user    ON conversations (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_doc     ON conversations (document_id);
CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages (conversation_id, created_at);