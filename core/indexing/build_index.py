"""Add chunk records to a persistent Chroma collection.

Embedding goes through the shared embedder so the document/query asymmetry
stays defined in one place. Writes are idempotent: a chunk id already in the
collection is skipped, so re-adding a document (or resuming an interrupted
run) never duplicates vectors.

Module form of src/3_embedding/build_index.py, trimmed to the one operation
the ingestion pipeline needs.
"""

from __future__ import annotations

from pathlib import Path

import chromadb

from core.indexing.embedder import MODEL_NAME, embed_documents

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_DIR = BASE_DIR / "data" / "vector_store"

# Bounds how much a failed run loses and how much sits in memory before a
# write. Ollama batches internally regardless.
BATCH_SIZE = 32


def open_collection(client, name: str):
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(
            name=name,
            # Vectors from this model are compared by angle, not magnitude.
            metadata={"hnsw:space": "cosine", "embedding_model": MODEL_NAME},
        )


def add_chunks(chunks: list[dict], collection_name: str, store_dir: Path = STORE_DIR) -> int:
    """Embed and store any of `chunks` not already in the collection. Returns
    the number of vectors actually added."""
    if not chunks:
        return 0

    store_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(store_dir))
    collection = open_collection(client, collection_name)

    stored = set(collection.get(include=[])["ids"]) if collection.count() else set()
    pending = [chunk for chunk in chunks if chunk["id"] not in stored]
    if not pending:
        return 0

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        collection.add(
            ids=[chunk["id"] for chunk in batch],
            embeddings=embed_documents([chunk["text"] for chunk in batch]),
            documents=[chunk["text"] for chunk in batch],
            metadatas=[
                {"source": chunk["source"], "page": chunk["page"]} for chunk in batch
            ],
        )

    return len(pending)


def remove_chunks(source: str, collection_name: str, store_dir: Path = STORE_DIR) -> None:
    """Delete every vector whose metadata says it came from `source`.

    Metadata-filtered delete, not id lookup — the caller doesn't need to
    know which chunk ids a document produced, only its filename, which is
    what a document is identified by everywhere else in the system too.
    """
    client = chromadb.PersistentClient(path=str(store_dir))
    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return  # nothing to remove from a collection that doesn't exist
    collection.delete(where={"source": source})
