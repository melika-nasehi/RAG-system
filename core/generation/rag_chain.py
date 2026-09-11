"""Question in, grounded answer out.

This is the thin layer that connects retrieval to generation. It stays thin
on purpose: retrieval quality and answer quality are separate failure modes,
and keeping the seam visible is what lets them be diagnosed apart. The result
carries the passages that produced it, so a wrong answer can always be traced
back to whether the wrong passages were fetched or the right ones were
misread.
"""

from dataclasses import dataclass
import os

from core.generation.generator import active_backend, generate
from core.generation.prompts import SYSTEM_PROMPT, build_user_message
from core.retrieval.retriever import DEFAULT_TOP_K, build_retriever

# Said when retrieval turns up nothing at all — a broken or empty collection.
NO_PASSAGES_MESSAGE = "هیچ متنی برای پاسخ‌گویی یافت نشد."

# Said when passages were retrieved but none scored above the confidence
# threshold: most likely the question is outside what the regulations cover.
LOW_CONFIDENCE_MESSAGE = (
    "متن مرتبطی برای پاسخ به این پرسش در آیین‌نامه‌های موجود یافت نشد."
)


@dataclass(frozen=True)
class Answer:
    """A generated answer alongside everything it was derived from."""

    question: str
    text: str
    passages: tuple
    backend: str
    # True when the chain declined to answer without calling the model —
    # empty retrieval, or a top score below the confidence threshold.
    refused: bool = False

    def sources(self):
        """Unique citations, in the order the passages were ranked."""
        seen = []
        for passage in self.passages:
            citation = passage.citation()
            if citation not in seen:
                seen.append(citation)
        return seen


def _resolve_min_score(explicit):
    """Threshold precedence: explicit argument, then MIN_RETRIEVAL_SCORE, then
    off. 0 or a negative value also means off."""
    if explicit is not None:
        return explicit if explicit > 0 else None
    raw = os.getenv("MIN_RETRIEVAL_SCORE", "").strip()
    if not raw:
        return None
    value = float(raw)
    return value if value > 0 else None


class RagChain:
    def __init__(
        self,
        retriever=None,
        top_k=DEFAULT_TOP_K,
        collection_name=None,
        mode=None,
        rerank=None,
        min_score=None,
    ):
        if retriever is not None:
            # An explicit retriever (or test double) always wins.
            self._retriever = retriever
        else:
            self._retriever = build_retriever(
                mode=mode,
                rerank=rerank,
                **({"collection_name": collection_name} if collection_name else {}),
            )
        self._top_k = top_k
        self._min_score = _resolve_min_score(min_score)

    def ask(self, question, top_k=None):
        passages = self._retriever.search(question, top_k=top_k or self._top_k)

        # No passages at all means the collection is empty or broken — worth
        # distinguishing from the model declining to answer.
        if not passages:
            return Answer(
                question=question,
                text=NO_PASSAGES_MESSAGE,
                passages=(),
                backend=active_backend(),
                refused=True,
            )

        # Confidence gate. `retrieval_score` is the dense cosine, carried
        # unchanged through fusion/reranking, so this comparison means the
        # same thing whatever the pipeline. Below the threshold, refuse here
        # rather than spend an LLM call on passages that don't answer.
        if self._min_score is not None:
            confidence = max((p.retrieval_score for p in passages), default=0.0)
            if confidence < self._min_score:
                return Answer(
                    question=question,
                    text=LOW_CONFIDENCE_MESSAGE,
                    passages=tuple(passages),
                    backend=active_backend(),
                    refused=True,
                )

        text = generate(SYSTEM_PROMPT, build_user_message(question, passages))

        return Answer(
            question=question,
            text=text.strip(),
            passages=tuple(passages),
            backend=active_backend(),
        )