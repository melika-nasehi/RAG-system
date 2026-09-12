

import argparse
import json
from pathlib import Path
import sys

import chromadb

sys.path.insert(0, str(Path(__file__).parent))
from embedder import MODEL_NAME, embed_documents, health_check

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHUNKS_DIR = BASE_DIR / "data" / "chunks"
STORE_DIR = BASE_DIR / "data" / "vector_store"

BATCH_SIZE = 32


def load_chunks(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def open_collection(client, name, reset):
    existing = {c.name for c in client.list_collections()}

    if name in existing and reset:
        client.delete_collection(name)
        existing.discard(name)

    if name in existing:
        return client.get_collection(name)

    return client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine", "embedding_model": MODEL_NAME},
    )


def pending_chunks(collection, chunks):
    if collection.count() == 0:
        return chunks

    stored = set(collection.get(include=[])["ids"])
    return [c for c in chunks if c["id"] not in stored]


def store_batch(collection, batch):
    vectors = embed_documents([c["text"] for c in batch])

    collection.add(
        ids=[c["id"] for c in batch],
        embeddings=vectors,
        documents=[c["text"] for c in batch],
        metadatas=[{"source": c["source"], "page": c["page"]} for c in batch],
    )


def build(chunks_file, collection_name, reset):
    chunks = load_chunks(chunks_file)
    print(f"{len(chunks)} chunks in {chunks_file.name}", flush=True)

    STORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    collection = open_collection(client, collection_name, reset)

    todo = pending_chunks(collection, chunks)
    if not todo:
        print(f"'{collection_name}' already complete")
        return collection

    if len(todo) < len(chunks):
        print(f"resuming — {len(chunks) - len(todo)} already embedded", flush=True)

    for start in range(0, len(todo), BATCH_SIZE):
        batch = todo[start:start + BATCH_SIZE]
        store_batch(collection, batch)
        print(f"  {min(start + BATCH_SIZE, len(todo))}/{len(todo)}", flush=True)

    return collection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", default="chunks_750_200.jsonl")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop the collection and rebuild from scratch",
    )
    args = parser.parse_args()

    chunks_file = CHUNKS_DIR / args.chunks
    if not chunks_file.exists():
        print(f"not found: {chunks_file}")
        return

    health_check()

    collection = build(chunks_file, chunks_file.stem, args.reset)

    print(f"\n'{chunks_file.stem}' holds {collection.count()} vectors")
    print(f"persisted to {STORE_DIR.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()