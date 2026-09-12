

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
