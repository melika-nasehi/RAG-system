

from dataclasses import dataclass
import os
from pathlib import Path

import chromadb

from core.indexing.embedder import embed_query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_DIR = BASE_DIR / "data" / "vector_store"

DEFAULT_COLLECTION = "chunks_500_100"

DEFAULT_MODE = "hybrid"

DEFAULT_TOP_K = 4

DEFAULT_CANDIDATES = 4


@dataclass(frozen=True)
class Passage:

    text: str
    source: str
    page: int
    score: float
    chunk_id: str
    retrieval_score: float = 0.0

    def citation(self):
        return f"{self.source}, صفحه {self.page}"


class Retriever:
    def __init__(self, collection_name=DEFAULT_COLLECTION, store_dir=STORE_DIR):
        client = chromadb.PersistentClient(path=str(store_dir))
        self._collection = client.get_collection(collection_name)

    def __len__(self):
        return self._collection.count()

    def search(self, question, top_k=DEFAULT_TOP_K, candidates=None):
        """Return the passages most relevant to a question, best first."""
        pool_size = max(candidates or DEFAULT_CANDIDATES, top_k)

        results = self._collection.query(
            query_embeddings=[embed_query(question)],
            n_results=pool_size,
            include=["documents", "metadatas", "distances"],
        )

        passages = [
            Passage(
                text=document,
                source=metadata["source"],
                page=metadata["page"],
                # Chroma reports cosine distance; the collection was built
                # with normalised vectors, so 1 - distance is the similarity.
                score=round(1 - distance, 4),
                chunk_id=chunk_id,
                retrieval_score=round(1 - distance, 4),
            )
            for document, metadata, distance, chunk_id in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                results["ids"][0],
            )
        ]

        return passages[:top_k]


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def build_retriever(mode=None, collection_name=DEFAULT_COLLECTION, rerank=None):

    mode = mode or os.getenv("RETRIEVER_MODE", DEFAULT_MODE)
    if rerank is None:
        rerank = _as_bool(os.getenv("RERANK", ""))

    if mode == "dense":
        base = Retriever(collection_name=collection_name)
    elif mode == "hybrid":
        from core.retrieval.hybrid import HybridRetriever

        base = HybridRetriever(collection_name=collection_name)
    else:
        raise ValueError(f"unknown retriever mode: {mode!r} (expected 'dense' or 'hybrid')")

    if not rerank:
        return base

    from core.retrieval.rerank import RerankingRetriever

    return RerankingRetriever(base)