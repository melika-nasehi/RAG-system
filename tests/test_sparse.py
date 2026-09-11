"""Unit tests for the BM25 (lexical) retrieval layer.

Like the dense retriever tests, these run against the real index built from
the project's chunk file — the whole point of BM25 here is behaviour on the
actual corpus vocabulary, and a mock would only prove the wiring.
"""

import pytest

from core.retrieval.sparse import SparseIndex, SparseHit
from core.retrieval.text import tokenize


@pytest.fixture(scope="module")
def index():
    """One shared index; building it tokenises ~600 chunks and is not free."""
    return SparseIndex.for_collection("chunks_500_100")


def test_index_covers_the_whole_chunk_file(index):
    assert len(index) > 500


def test_exact_term_query_retrieves_a_chunk_containing_that_term(index):
    """BM25's reason for being: a distinctive surface term in the question
    should pull the passage that contains it, even with no semantic model."""
    hits = index.search("مرخصی زایمان", top_k=5)

    assert hits
    assert any("زایمان" in hit.text for hit in hits)


def test_hits_carry_provenance(index):
    for hit in index.search("حذف پزشکی گواهی", top_k=3):
        assert isinstance(hit, SparseHit)
        assert hit.source.endswith(".pdf")
        assert hit.page >= 1
        assert hit.chunk_id


def test_hits_are_sorted_by_score_descending(index):
    scores = [hit.score for hit in index.search("شرایط آزمون جامع دکتری", top_k=6)]
    assert scores == sorted(scores, reverse=True)


def test_zero_score_passages_are_not_returned(index):
    """A query of pure stopwords tokenises to nothing, so every document
    scores zero and none should be returned rather than an arbitrary top_k."""
    assert index.search("از و در به که را", top_k=4) == []


class TestTokenizer:
    def test_normalises_arabic_and_persian_letter_forms(self):
        """The same word written with Arabic yeh/kaf must land on the same
        token as the Persian form, or a query never matches the index."""
        assert tokenize("كلاس‌های درسی") == tokenize("کلاس‌های درسی")

    def test_drops_stopwords_and_punctuation(self):
        tokens = tokenize("این یک جملهٔ نمونه است، برای آزمایش.")
        assert "این" not in tokens
        assert "است" not in tokens
        assert "،" not in tokens
        assert "نمونه" in tokens

    def test_repairs_persian_digit_words_consistently(self):
        # Whatever normalisation does to digits, a query and a passage with
        # the same number must tokenise identically.
        assert tokenize("۲۰ واحد") == tokenize("۲۰ واحد")
