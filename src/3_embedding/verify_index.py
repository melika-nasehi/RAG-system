"""Sanity-check the built collection before anything relies on it.

A successful write says rows exist, not that they hold the right vectors,
the right metadata, or vectors that behave sensibly under similarity search.
Each check below is one thing that could be silently wrong.
"""

import json
from pathlib import Path
import sys

import chromadb

sys.path.insert(0, str(Path(__file__).parent))
from embedder import VECTOR_DIM, embed_query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHUNKS_DIR = BASE_DIR / "data" / "chunks"
STORE_DIR = BASE_DIR / "data" / "vector_store"

COLLECTION = "chunks_750_200"
CHUNKS_FILE = "chunks_750_200.jsonl"


def load_chunks():
    path = CHUNKS_DIR / CHUNKS_FILE
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main():
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    collection = client.get_collection(COLLECTION)
    chunks = load_chunks()

    print(f"collection: {COLLECTION}")
    print(f"  stored    {collection.count()}")
    print(f"  expected  {len(chunks)}")

    # --- every chunk present, none duplicated ---
    stored_ids = collection.get(include=[])["ids"]
    expected_ids = {c["id"] for c in chunks}

    missing = expected_ids - set(stored_ids)
    duplicated = len(stored_ids) - len(set(stored_ids))

    print(f"  missing   {len(missing)}")
    print(f"  duplicate {duplicated}")

    # --- vectors have the right shape and aren't degenerate ---
    sample = collection.get(limit=5, include=["embeddings", "documents", "metadatas"])

    dims = {len(v) for v in sample["embeddings"]}
    print(f"\nvector dims in sample: {dims}")

    # An all-zero or constant vector means the embedding call failed quietly.
    for i, vector in enumerate(sample["embeddings"]):
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude < 1e-6:
            print(f"  WARNING: vector {i} is near-zero")

    # --- metadata survived ---
    print("\nsample metadata:")
    for meta in sample["metadatas"][:3]:
        print(f"  {meta}")

    # --- retrieval actually retrieves ---
    questions = [
        "حداکثر تعداد واحد درسی در هر نیمسال چند است؟",
        "شرایط استفاده از مرخصی تحصیلی چیست؟",
        "مقررات استفاده از سالن ورزشی",
    ]

    print("\nretrieval spot-check:")
    for question in questions:
        results = collection.query(
            query_embeddings=[embed_query(question)],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )

        print(f"\n  Q: {question}")
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            snippet = " ".join(doc.split())[:90]
            print(f"    {1 - dist:.3f}  {meta['source'][:28]} p{meta['page']}")
            print(f"           {snippet}...")


if __name__ == "__main__":
    main()