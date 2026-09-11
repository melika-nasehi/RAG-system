"""Unit tests for the retrieval layer.

These run against the real Chroma collection built during the project, not
a mock store — retrieval quality depends on the actual index, and mocking it
would only prove the code calls a fake object correctly.
"""

import pytest

from core.retrieval.retriever import Retriever


@pytest.fixture(scope="module")
def retriever():
    """One Retriever instance shared across tests in this file — opening the
    Chroma connection is not free, and nothing here mutates state."""
    return Retriever()


def test_collection_has_expected_size(retriever):
    """A rough sanity check: the collection should hold roughly the number
    of chunks the 500/100 configuration produced. Not exact, since re-runs
    of indexing could add a handful, but a collapse to zero or a wildly
    different count would signal the wrong collection got loaded."""
    assert len(retriever) > 500


def test_search_returns_requested_number_of_passages(retriever):
    results = retriever.search("حداکثر واحد درسی چند است؟", top_k=4)
    assert len(results) == 4


def test_search_returns_passages_sorted_by_score(retriever):
    results = retriever.search("شرایط مرخصی تحصیلی چیست؟", top_k=4)
    scores = [p.score for p in results]
    assert scores == sorted(scores, reverse=True)


def test_relevant_query_hits_expected_document(retriever):
    """Reproduces the retrieval-hit check from the evaluation set: a direct
    question about credit limits should surface the main academic
    regulation document, not an unrelated one."""
    results = retriever.search("حداکثر تعداد واحد درسی در هر نیمسال چند است؟", top_k=4)
    sources = [p.source for p in results]

    assert any("مقررات آموزشی" in source for source in sources)


def test_each_passage_has_valid_citation(retriever):
    """Every passage must carry enough provenance to be cited — this is the
    whole point of keeping page and source with the chunk."""
    results = retriever.search("شرایط استفاده از خوابگاه دانشجویی", top_k=3)

    for passage in results:
        assert passage.source.endswith(".pdf")
        assert passage.page >= 1
        assert "صفحه" in passage.citation()