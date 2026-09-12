

import pytest

from core.generation import rag_chain as rag_chain_module
from core.generation.rag_chain import LOW_CONFIDENCE_MESSAGE, NO_PASSAGES_MESSAGE, RagChain
from core.retrieval.retriever import Passage


class FakeRetriever:
    def __init__(self, passages):
        self._passages = passages

    def search(self, question, top_k=None):
        return self._passages[:top_k] if top_k else self._passages


def make_passage(retrieval_score, chunk_id="c1"):
    return Passage(
        text="متن نمونه",
        source="سند.pdf",
        page=1,
        score=retrieval_score,
        chunk_id=chunk_id,
        retrieval_score=retrieval_score,
    )


@pytest.fixture
def spy_generate(monkeypatch):

    calls = []

    def fake_generate(system_prompt, user_message, backend=None):
        calls.append(user_message)
        return "پاسخ مدل"

    monkeypatch.setattr(rag_chain_module, "generate", fake_generate)
    return calls


def test_gate_disabled_by_default_answers_even_a_low_score(spy_generate):
    chain = RagChain(retriever=FakeRetriever([make_passage(0.10)]))
    answer = chain.ask("سوال")

    assert answer.refused is False
    assert answer.text == "پاسخ مدل"
    assert len(spy_generate) == 1


def test_below_threshold_refuses_without_calling_the_llm(spy_generate):

    chain = RagChain(retriever=FakeRetriever([make_passage(0.43)]), min_score=0.55)
    answer = chain.ask("هزینه غذای سلف چقدر است؟")

    assert answer.refused is True
    assert answer.text == LOW_CONFIDENCE_MESSAGE
    assert spy_generate == []  # LLM never reached
    assert len(answer.passages) == 1  # retrieved context still attached


def test_above_threshold_answers_normally(spy_generate):

    chain = RagChain(retriever=FakeRetriever([make_passage(0.72)]), min_score=0.55)
    answer = chain.ask("مدت مرخصی زایمان چقدر است؟")

    assert answer.refused is False
    assert answer.text == "پاسخ مدل"
    assert len(spy_generate) == 1


def test_score_exactly_at_threshold_is_allowed(spy_generate):
    chain = RagChain(retriever=FakeRetriever([make_passage(0.55)]), min_score=0.55)
    assert chain.ask("سوال").refused is False


def test_confidence_is_the_max_over_returned_passages(spy_generate):

    chain = RagChain(
        retriever=FakeRetriever([make_passage(0.30, "a"), make_passage(0.61, "b")]),
        min_score=0.55,
    )
    assert chain.ask("سوال").refused is False


def test_threshold_reads_the_environment(monkeypatch, spy_generate):
    monkeypatch.setenv("MIN_RETRIEVAL_SCORE", "0.60")
    chain = RagChain(retriever=FakeRetriever([make_passage(0.50)]))
    answer = chain.ask("سوال")

    assert answer.refused is True
    assert spy_generate == []


def test_explicit_zero_disables_even_with_env_set(monkeypatch, spy_generate):
    monkeypatch.setenv("MIN_RETRIEVAL_SCORE", "0.60")
    chain = RagChain(retriever=FakeRetriever([make_passage(0.50)]), min_score=0)
    assert chain.ask("سوال").refused is False


def test_empty_retrieval_still_refuses_with_its_own_message(spy_generate):
    chain = RagChain(retriever=FakeRetriever([]), min_score=0.55)
    answer = chain.ask("سوال")

    assert answer.refused is True
    assert answer.text == NO_PASSAGES_MESSAGE
    assert answer.passages == ()
    assert spy_generate == []
