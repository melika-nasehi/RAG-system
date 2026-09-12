

import pytest

from core.generation.rag_chain import Answer, RagChain
from core.retrieval.retriever import Passage


class FakeRetriever:


    def __init__(self, passages):
        self._passages = passages

    def search(self, question, top_k=None):
        return self._passages[:top_k] if top_k else self._passages


def make_passage(text="متن نمونه", source="سند نمونه.pdf", page=1, score=0.7):
    return Passage(text=text, source=source, page=page, score=score, chunk_id="test_1")


def test_no_passages_returns_explicit_message_without_calling_llm():

    chain = RagChain(retriever=FakeRetriever([]))
    answer = chain.ask("سوال بی‌ربط")

    assert isinstance(answer, Answer)
    assert answer.passages == ()
    assert "یافت نشد" in answer.text


def test_sources_deduplicates_repeated_citations():

    passages = [
        make_passage(source="سند الف.pdf", page=1),
        make_passage(source="سند الف.pdf", page=1),
        make_passage(source="سند ب.pdf", page=2),
    ]
    answer = Answer(question="q", text="a", passages=tuple(passages), backend="test")

    assert answer.sources() == ["سند الف.pdf, صفحه 1", "سند ب.pdf, صفحه 2"]


def test_sources_preserves_ranking_order():

    passages = [
        make_passage(source="سند ج.pdf", page=5),
        make_passage(source="سند آ.pdf", page=1),
    ]
    answer = Answer(question="q", text="a", passages=tuple(passages), backend="test")

    assert answer.sources() == ["سند ج.pdf, صفحه 5", "سند آ.pdf, صفحه 1"]


@pytest.mark.integration
def test_full_chain_answers_a_known_question():

    chain = RagChain()
    answer = chain.ask("حداکثر تعداد واحد درسی در هر نیمسال چند است؟")

    assert "20" in answer.text or "۲۰" in answer.text
    assert len(answer.passages) > 0