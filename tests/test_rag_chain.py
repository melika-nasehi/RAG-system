"""Unit tests for the RAG chain.

Most tests here use a fake retriever with fixed passages, so they run
without hitting the vector store or the LLM API — fast, free, and
deterministic. One test at the bottom does call the real chain end-to-end,
marked separately so it can be skipped when quota is tight.
"""

import pytest

from core.generation.rag_chain import Answer, RagChain
from core.retrieval.retriever import Passage


class FakeRetriever:
    """A stand-in that returns whatever passages the test hands it, instead
    of querying Chroma. This isolates RagChain's own logic — the no-passage
    branch, source deduplication — from retrieval and generation."""

    def __init__(self, passages):
        self._passages = passages

    def search(self, question, top_k=None):
        return self._passages[:top_k] if top_k else self._passages


def make_passage(text="متن نمونه", source="سند نمونه.pdf", page=1, score=0.7):
    return Passage(text=text, source=source, page=page, score=score, chunk_id="test_1")


def test_no_passages_returns_explicit_message_without_calling_llm():
    """When retrieval finds nothing, the chain should say so directly and
    never reach the LLM — there's nothing for it to answer from."""
    chain = RagChain(retriever=FakeRetriever([]))
    answer = chain.ask("سوال بی‌ربط")

    assert isinstance(answer, Answer)
    assert answer.passages == ()
    assert "یافت نشد" in answer.text


def test_sources_deduplicates_repeated_citations():
    """The same document/page can appear as more than one chunk; sources()
    should list each citation once, in first-seen order."""
    passages = [
        make_passage(source="سند الف.pdf", page=1),
        make_passage(source="سند الف.pdf", page=1),
        make_passage(source="سند ب.pdf", page=2),
    ]
    answer = Answer(question="q", text="a", passages=tuple(passages), backend="test")

    assert answer.sources() == ["سند الف.pdf, صفحه 1", "سند ب.pdf, صفحه 2"]


def test_sources_preserves_ranking_order():
    """Citations should appear in the order passages were ranked, not
    alphabetically or by page number."""
    passages = [
        make_passage(source="سند ج.pdf", page=5),
        make_passage(source="سند آ.pdf", page=1),
    ]
    answer = Answer(question="q", text="a", passages=tuple(passages), backend="test")

    assert answer.sources() == ["سند ج.pdf, صفحه 5", "سند آ.pdf, صفحه 1"]


@pytest.mark.integration
def test_full_chain_answers_a_known_question():
    """End-to-end check against the real retriever and LLM. Marked as an
    integration test so it can be excluded from fast local runs and CI
    stages that shouldn't spend API quota."""
    chain = RagChain()
    answer = chain.ask("حداکثر تعداد واحد درسی در هر نیمسال چند است؟")

    assert "20" in answer.text or "۲۰" in answer.text
    assert len(answer.passages) > 0