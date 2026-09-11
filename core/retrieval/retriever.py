"""Retrieve the passages most relevant to a question.

This is deliberately independent of answer generation: it takes a question
and returns passages with their scores and provenance, nothing more. Keeping
it that way is what makes retrieval quality measurable on its own, separately
from whether the LLM then writes a good answer.

The two-stage shape (fetch a wider candidate pool, return a narrower final
set) is here from the start so a reranker can slot into the gap without the
call sites changing.
"""

from dataclasses import dataclass
import os
from pathlib import Path

import chromadb

from core.indexing.embedder import embed_query

# core/retrieval/retriever.py -> parent.parent = core/ -> parent = project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_DIR = BASE_DIR / "data" / "vector_store"

DEFAULT_COLLECTION = "chunks_500_100"

# "hybrid" (dense + BM25) or "dense". Hybrid is the default because it is
# strictly a superset — it can only add lexical matches the embedding step
# missed — and the cost of building the sparse index is paid once.
DEFAULT_MODE = "hybrid"

# Passages handed to the generator. More context isn't automatically better —
# an LLM given ten passages has more chance to answer from the wrong one.
DEFAULT_TOP_K = 4

# Candidates fetched before any reranking. With no reranker in place this is
# the same as TOP_K; the parameter exists so adding one is a config change.
DEFAULT_CANDIDATES = 4


@dataclass(frozen=True)
class Passage:
    """A retrieved chunk with enough provenance to cite it.

    `score` is whatever the *last* stage in the pipeline ranked on — cosine
    from dense retrieval, an RRF value from fusion, a cross-encoder
    probability after reranking. It is only comparable within one result set.

    `retrieval_score` is always the dense cosine similarity (0.0 if the
    passage was surfaced by BM25 alone and dense never scored it). It is
    carried unchanged through fusion and reranking so that a confidence check
    has one stable, interpretable signal regardless of which stages are on.
    """

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
    """The retriever the rest of the system should use.

    `mode` ("dense" | "hybrid") falls back to the RETRIEVER_MODE environment
    variable, then to DEFAULT_MODE. `rerank` (bool) falls back to the RERANK
    variable — when on, the base retriever is wrapped in a cross-encoder
    reranking stage. So the whole pipeline shape is a config change, never a
    code change.

    Every heavier import (hybrid → hazm/rank-bm25, rerank → sentence-
    transformers) is deferred, so a deployment only pays for the stages it
    switches on.
    """
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