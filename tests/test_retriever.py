

import pytest

from core.retrieval.retriever import Retriever


@pytest.fixture(scope="module")
def retriever():

    return Retriever()


def test_collection_has_expected_size(retriever):

    assert len(retriever) > 500


def test_search_returns_requested_number_of_passages(retriever):
    results = retriever.search("حداکثر واحد درسی چند است؟", top_k=4)
    assert len(results) == 4


def test_search_returns_passages_sorted_by_score(retriever):
    results = retriever.search("شرایط مرخصی تحصیلی چیست؟", top_k=4)
    scores = [p.score for p in results]
    assert scores == sorted(scores, reverse=True)


def test_relevant_query_hits_expected_document(retriever):

    results = retriever.search("حداکثر تعداد واحد درسی در هر نیمسال چند است؟", top_k=4)
    sources = [p.source for p in results]

    assert any("مقررات آموزشی" in source for source in sources)


def test_each_passage_has_valid_citation(retriever):

    results = retriever.search("شرایط استفاده از خوابگاه دانشجویی", top_k=3)

    for passage in results:
        assert passage.source.endswith(".pdf")
        assert passage.page >= 1
        assert "صفحه" in passage.citation()