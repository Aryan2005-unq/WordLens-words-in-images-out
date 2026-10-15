"""PostgreSQL operations for photo embeddings."""

from uuid import UUID
from datetime import date

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from photo_search.config import settings


def connect() -> psycopg.Connection:
    """Open a short-lived database connection using separate settings."""
    connection = psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=5,
        application_name="photo-search",
    )
    register_vector(connection)
    return connection


def initialize_database() -> None:
    """Ensure the extension and application table exist."""
    with connect() as connection:
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS photos (
                id UUID PRIMARY KEY,
                stored_name TEXT NOT NULL UNIQUE,
                sha256 CHAR(64) NOT NULL UNIQUE,
                embedding VECTOR(512) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        connection.execute(
            "ALTER TABLE photos ADD COLUMN IF NOT EXISTS captured_date DATE"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS evaluation_cases (
                   query TEXT PRIMARY KEY,
                   relevant_photo_ids UUID[] NOT NULL,
                   updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
               )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS photos_captured_date_idx ON photos (captured_date)"
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS photos_embedding_cosine_idx
               ON photos USING hnsw (embedding vector_cosine_ops)"""
        )


def add_photo(
    photo_id: UUID,
    stored_name: str,
    sha256: str,
    embedding,
    captured_date: date | None,
) -> bool:
    """Insert an image and its embedding. Return False for duplicate image data."""
    with connect() as connection:
        result = connection.execute(
            """INSERT INTO photos (id, stored_name, sha256, embedding, captured_date)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (sha256) DO NOTHING
               RETURNING id""",
            (photo_id, stored_name, sha256, Vector(embedding), captured_date),
        )
        if result.fetchone() is not None:
            return True
        if captured_date is not None:
            connection.execute(
                """UPDATE photos
                   SET captured_date = COALESCE(captured_date, %s)
                   WHERE sha256 = %s""",
                (captured_date, sha256),
            )
        return False


def search_photos(
    query_embedding,
    limit: int = 12,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """Return nearest photos ordered by cosine similarity."""
    with connect() as connection:
        vector = Vector(query_embedding)
        if start_date is None and end_date is None:
            rows = connection.execute(
                """SELECT id, stored_name, captured_date,
                          1 - (embedding <=> %s) AS similarity
                   FROM photos
                   ORDER BY embedding <=> %s
                   LIMIT %s""",
                (vector, vector, limit),
            ).fetchall()
        else:
            # Materialize the date-filtered rows before ranking so approximate HNSW
            # traversal cannot return too few results after the date filter.
            rows = connection.execute(
                """WITH candidates AS MATERIALIZED (
                       SELECT id, stored_name, captured_date, embedding
                       FROM photos
                       WHERE (%s::date IS NULL OR captured_date >= %s)
                         AND (%s::date IS NULL OR captured_date <= %s)
                   )
                   SELECT id, stored_name, captured_date,
                          1 - (embedding <=> %s) AS similarity
                   FROM candidates
                   ORDER BY embedding <=> %s
                   LIMIT %s""",
                (start_date, start_date, end_date, end_date, vector, vector, limit),
            ).fetchall()
    return [
        {
            "id": row[0],
            "stored_name": row[1],
            "captured_date": row[2],
            "similarity": float(row[3]),
        }
        for row in rows
    ]


def photo_count() -> int:
    with connect() as connection:
        return connection.execute("SELECT COUNT(*) FROM photos").fetchone()[0]


def list_photos() -> list[dict]:
    """Return indexed photos for the evaluation labeling interface."""
    with connect() as connection:
        rows = connection.execute(
            """SELECT id, stored_name, captured_date FROM photos
               ORDER BY captured_date DESC NULLS LAST, created_at DESC"""
        ).fetchall()
    return [
        {"id": str(row[0]), "stored_name": row[1], "captured_date": row[2]}
        for row in rows
    ]


def save_evaluation_case(query: str, relevant_photo_ids: list[UUID]) -> None:
    """Insert or update one query's human-labeled relevant photo IDs."""
    with connect() as connection:
        connection.execute(
            """INSERT INTO evaluation_cases (query, relevant_photo_ids)
               VALUES (%s, %s)
               ON CONFLICT (query) DO UPDATE
               SET relevant_photo_ids = EXCLUDED.relevant_photo_ids,
                   updated_at = NOW()""",
            (query, relevant_photo_ids),
        )


def list_evaluation_cases() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT query, relevant_photo_ids FROM evaluation_cases
               ORDER BY updated_at DESC"""
        ).fetchall()
    return [
        {"query": row[0], "relevant_photo_ids": [str(item) for item in row[1]]}
        for row in rows
    ]
