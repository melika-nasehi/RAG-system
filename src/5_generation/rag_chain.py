"""Question in, grounded answer out.

This is the thin layer that connects retrieval to generation. It stays thin
on purpose: retrieval quality and answer quality are separate failure modes,
and keeping the seam visible is what lets them be diagnosed apart. The result
carries the passages that produced it, so a wrong answer can always be traced
back to whether the wrong passages were fetched or the right ones were
misread.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "4_retrieval"))

from generator import active_backend, generate
from prompts import SYSTEM_PROMPT, build_user_message
from retriever import DEFAULT_TOP_K, Retriever


@dataclass(frozen=True)
class Answer:
    """A generated answer alongside everything it was derived from."""

    question: str
    text: str
    passages: tuple
    backend: str

    def sources(self):
        """Unique citations, in the order the passages were ranked."""
        seen = []
        for passage in self.passages:
            citation = passage.citation()
            if citation not in seen:
                seen.append(citation)
        return seen


class RagChain:
    def __init__(self, retriever=None, top_k=DEFAULT_TOP_K):
        self._retriever = retriever or Retriever()
        self._top_k = top_k

    def ask(self, question, top_k=None):
        passages = self._retriever.search(question, top_k=top_k or self._top_k)

        # No passages at all means the collection is empty or broken — worth
        # distinguishing from the model declining to answer.
        if not passages:
            return Answer(
                question=question,
                text="هیچ متنی برای پاسخ‌گویی یافت نشد.",
                passages=(),
                backend=active_backend(),
            )

        text = generate(SYSTEM_PROMPT, build_user_message(question, passages))

        return Answer(
            question=question,
            text=text.strip(),
            passages=tuple(passages),
            backend=active_backend(),
        )