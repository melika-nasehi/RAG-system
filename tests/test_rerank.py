

import pytest

from core.retrieval.rerank import CrossEncoderReranker, RerankingRetriever
from core.retrieval.retriever import Passage


def passage(chunk_id, score=0.5, text=None):
    return Passage(
        text=text or f"متن {chunk_id}",
        source="سند.pdf",
        page=1,
        score=score,
        chunk_id=chunk_id,
    )


class FakeModel:

    def __init__(self, logits_by_text):
        self._logits = logits_by_text

    def predict(self, pairs, **kwargs):
        return [self._logits[text] for _question, text in pairs]


def reranker_with(logits_by_text):
    reranker = CrossEncoderReranker(model_name="unused")
    reranker._model = FakeModel(logits_by_text)
    return reranker


class FakeBase:
    def __init__(self, passages):
        self._passages = passages
        self.last_top_k = None

    def __len__(self):
        return len(self._passages)

    def search(self, question, top_k=4):
        self.last_top_k = top_k
        return self._passages[:top_k]


def test_rerank_reorders_by_cross_encoder_score():
    passages = [passage("A"), passage("B"), passage("C")]
    reranker = reranker_with({"متن A": -2.0, "متن B": 3.0, "متن C": 0.5})

    ordered = [p.chunk_id for p in reranker.rerank("q", passages, top_k=3)]
    assert ordered == ["B", "C", "A"]


def test_rerank_truncates_to_top_k():
    passages = [passage(c) for c in "ABCDE"]
    reranker = reranker_with({f"متن {c}": i for i, c in enumerate("ABCDE")})
    assert len(reranker.rerank("q", passages, top_k=2)) == 2


def test_rerank_writes_a_probability_like_score():
    reranker = reranker_with({"متن A": 0.0})  # sigmoid(0) == 0.5
    [result] = reranker.rerank("q", [passage("A", score=0.99)], top_k=1)
    assert result.score == pytest.approx(0.5, abs=1e-6)


def test_rerank_empty_input_returns_empty():
    assert reranker_with({}).rerank("q", [], top_k=4) == []


def test_reranking_retriever_pulls_a_wide_pool_then_narrows():
    base = FakeBase([passage(c) for c in "ABCDEFGHIJ"])
    reranker = reranker_with({f"متن {c}": -ord(c) for c in "ABCDEFGHIJ"})  # A best
    retriever = RerankingRetriever(base, reranker=reranker, candidates=8)

    results = retriever.search("q", top_k=3)

    assert base.last_top_k == 8  # asked the base for the wide pool
    assert len(results) == 3
    assert results[0].chunk_id == "A"


def test_reranking_retriever_keeps_the_search_signature():
    base = FakeBase([passage(c) for c in "ABCDE"])
    reranker = reranker_with({f"متن {c}": 0.0 for c in "ABCDE"})
    retriever = RerankingRetriever(base, reranker=reranker, candidates=4)

    assert len(retriever) == 5
    assert retriever.search("q", top_k=2)


@pytest.mark.integration
def test_real_cross_encoder_prefers_the_relevant_passage():
    reranker = CrossEncoderReranker()
    question = "مدت مجاز مرخصی زایمان چقدر است؟"
    passages = [
        passage("irrelevant", text="شرایط استفاده از خوابگاه دانشجویی و مقررات انضباطی."),
        passage("relevant", text="مرخصی زایمان دانشجو حداکثر دو نیمسال تحصیلی است."),
        passage("topical", text="دانشجو باید حداقل ۱۲ واحد در هر نیمسال انتخاب کند."),
    ]
    ordered = reranker.rerank(question, passages, top_k=3)
    assert ordered[0].chunk_id == "relevant"
    assert ordered[0].score > 0.5
