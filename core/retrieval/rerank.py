"""Cross-encoder reranking of retrieved candidates.

Bi-encoder retrieval (dense or BM25) scores a query and a passage
independently and compares the two vectors. A cross-encoder instead reads the
query and the passage together, so it can weigh how the specific words
interact — which is exactly what is needed to tell a passage that answers the
question from one that merely shares its topic.

It is far too slow to run over the whole collection, so it sits after
retrieval: pull a wide candidate pool cheaply, then let the cross-encoder
re-order the top 10-20 down to the final few the generator sees.

The model is multilingual (XLM-RoBERTa backbone); the fine-tuning data did
not include Persian, but the encoder was pretrained on it and the separation
on this corpus is clean in practice. It is loaded lazily and only when
reranking is actually switched on, so a deployment that leaves it off never
pays the import or the download.
"""

from __future__ import annotations

from dataclasses import replace
import math
import os

from core.retrieval.retriever import DEFAULT_TOP_K, Passage

# ~120 MB. Override with RERANK_MODEL for a stronger (heavier) reranker.
DEFAULT_MODEL = os.getenv(
    "RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

# Candidates fed to the cross-encoder. Wider than the final top_k so a passage
# retrieval ranked low can still be rescued, but bounded because every
# candidate is a full forward pass.
RERANK_CANDIDATES = 15

_MAX_LENGTH = 512


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class CrossEncoderReranker:
    """Reorders passages by a cross-encoder relevance score. The score written
    onto each returned Passage is the sigmoid of the model logit, in (0, 1),
    so it can be read as a rough relevance probability."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self._model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, max_length=_MAX_LENGTH)
        return self._model

    def rerank(
        self, question: str, passages: list[Passage], top_k: int = DEFAULT_TOP_K
    ) -> list[Passage]:
        if not passages:
            return []

        model = self._ensure_model()
        logits = model.predict(
            [(question, passage.text) for passage in passages],
            show_progress_bar=False,
        )

        rescored = [
            replace(passage, score=round(_sigmoid(float(logit)), 6))
            for passage, logit in zip(passages, logits)
        ]
        rescored.sort(key=lambda passage: passage.score, reverse=True)
        return rescored[:top_k]


class RerankingRetriever:
    """A retriever wrapper: fetch a wide pool from `base`, then rerank it down.

    Presents the same `search(question, top_k=...)` signature as every other
    retriever, so RagChain does not know it is there."""

    def __init__(self, base, reranker: CrossEncoderReranker | None = None,
                 candidates: int = RERANK_CANDIDATES):
        self._base = base
        self._reranker = reranker or CrossEncoderReranker()
        self._candidates = candidates

    def __len__(self) -> int:
        return len(self._base)

    def search(
        self, question: str, top_k: int = DEFAULT_TOP_K, candidates: int | None = None
    ) -> list[Passage]:
        pool = max(candidates or self._candidates, top_k)
        return self._reranker.rerank(question, self._base.search(question, top_k=pool), top_k)
