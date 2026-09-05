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
from pathlib import Path
import sys

import chromadb

sys.path.insert(0, str(Path(__file__).parent.parent / "3_embedding"))
from embedder import embed_query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_DIR = BASE_DIR / "data" / "vector_store"

DEFAULT_COLLECTION = "chunks_500_100"

# Passages handed to the generator. More context isn't automatically better —
# an LLM given ten passages has more chance to answer from the wrong one.
DEFAULT_TOP_K = 4

# Candidates fetched before any reranking. With no reranker in place this is
# the same as TOP_K; the parameter exists so adding one is a config change.
DEFAULT_CANDIDATES = 4


@dataclass(frozen=True)
class Passage:
    """A retrieved chunk with enough provenance to cite it."""

    text: str
    source: str
    page: int
    score: float
    chunk_id: str

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
            )
            for document, metadata, distance, chunk_id in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                results["ids"][0],
            )
        ]

        return passages[:top_k]