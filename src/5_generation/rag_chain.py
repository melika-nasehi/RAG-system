
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

    question: str
    text: str
    passages: tuple
    backend: str

    def sources(self):
        seen = []
        for passage in self.passages:
            citation = passage.citation()
            if citation not in seen:
                seen.append(citation)
        return seen


class RagChain:
    def __init__(self, retriever=None, top_k=DEFAULT_TOP_K, collection_name=None):
        if retriever is not None:
            self._retriever = retriever
        elif collection_name is not None:
            self._retriever = Retriever(collection_name=collection_name)
        else:
            self._retriever = Retriever()
        self._top_k = top_k

    def ask(self, question, top_k=None):
        passages = self._retriever.search(question, top_k=top_k or self._top_k)

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