CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS photos (
    id UUID PRIMARY KEY,
    stored_name TEXT NOT NULL UNIQUE,
    sha256 CHAR(64) NOT NULL UNIQUE,
    embedding VECTOR(512) NOT NULL,
    captured_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE photos ADD COLUMN IF NOT EXISTS captured_date DATE;
CREATE INDEX IF NOT EXISTS photos_captured_date_idx ON photos (captured_date);

CREATE INDEX IF NOT EXISTS photos_embedding_cosine_idx
    ON photos USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS evaluation_cases (
    query TEXT PRIMARY KEY,
    relevant_photo_ids UUID[] NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
