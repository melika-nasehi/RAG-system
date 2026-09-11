"""Dense and lexical retrieval, combined.

Each retriever is strong where the other is weak: embeddings match on meaning
across different wording, BM25 matches exact terms the embedding model would
smooth over. Reciprocal Rank Fusion combines their two rankings without
needing their scores to be comparable — a passage's contribution depends
only on its position in each list, so a cosine similarity and a BM25 score
never have to be put on the same scale.

The public shape is identical to the dense Retriever: `search(question,
top_k=...)` returns a list of Passage, best first. RagChain does not know or
care which retriever it holds.
"""

from __future__ import annotations

from dataclasses import replace

from core.retrieval.retriever import DEFAULT_COLLECTION, DEFAULT_TOP_K, Passage, Retriever
from core.retrieval.sparse import SparseIndex

# RRF's smoothing constant. 60 is the value from the original Cormack et al.
# paper and the de facto default; it flattens the weight of the very top
# ranks just enough that a single retriever cannot dominate the fused order.
RRF_K = 60

# How many candidates to pull from each retriever before fusing. Wider than
# the final top_k so a passage ranked, say, 8th by one method and 2nd by the
# other still surfaces.
DEFAULT_CANDIDATES = 20


class HybridRetriever:
    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        dense: Retriever | None = None,
        sparse: SparseIndex | None = None,
        rrf_k: int = RRF_K,
        candidates: int = DEFAULT_CANDIDATES,
    ):
        self._dense = dense or Retriever(collection_name=collection_name)
        self._sparse = sparse or SparseIndex.for_collection(collection_name)
        self._rrf_k = rrf_k
        self._candidates = candidates

    def __len__(self) -> int:
        return len(self._dense)

    def search(
        self, question: str, top_k: int = DEFAULT_TOP_K, candidates: int | None = None
    ) -> list[Passage]:
        pool = max(candidates or self._candidates, top_k)

        dense_hits = self._dense.search(question, top_k=pool)
        sparse_hits = self._sparse.search(question, top_k=pool)

        return self._fuse(dense_hits, sparse_hits, top_k)

    def _fuse(
        self, dense_hits: list[Passage], sparse_hits, top_k: int
    ) -> list[Passage]:
        fused: dict[str, float] = {}
        passages: dict[str, Passage] = {}

        for rank, passage in enumerate(dense_hits):
            fused[passage.chunk_id] = fused.get(passage.chunk_id, 0.0) + self._rrf(rank)
            passages[passage.chunk_id] = passage

        for rank, hit in enumerate(sparse_hits):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + self._rrf(rank)
            passages.setdefault(
                hit.chunk_id,
                Passage(
                    text=hit.text,
                    source=hit.source,
                    page=hit.page,
                    score=hit.score,
                    chunk_id=hit.chunk_id,
                    # BM25 surfaced this on its own; dense never scored it, so
                    # its dense-confidence signal is absent (left at 0.0).
                    retrieval_score=0.0,
                ),
            )

        ordered = sorted(fused, key=lambda cid: fused[cid], reverse=True)[:top_k]

        # The reported score becomes the fused RRF score, so a caller logging
        # answer.passages[0].score sees the value the ranking was actually made
        # on rather than a leftover cosine or BM25 number.
        return [replace(passages[cid], score=round(fused[cid], 6)) for cid in ordered]

    def _rrf(self, rank: int) -> float:
        return 1.0 / (self._rrf_k + rank + 1)
