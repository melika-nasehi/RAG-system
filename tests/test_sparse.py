

import pytest

from core.retrieval.sparse import SparseIndex, SparseHit
from core.retrieval.text import tokenize


@pytest.fixture(scope="module")
def index():
    return SparseIndex.for_collection("chunks_500_100")


def test_index_covers_the_whole_chunk_file(index):
    assert len(index) > 500


def test_exact_term_query_retrieves_a_chunk_containing_that_term(index):

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

    assert index.search("از و در به که را", top_k=4) == []


class TestTokenizer:
    def test_normalises_arabic_and_persian_letter_forms(self):

        assert tokenize("كلاس‌های درسی") == tokenize("کلاس‌های درسی")

    def test_drops_stopwords_and_punctuation(self):
        tokens = tokenize("این یک جملهٔ نمونه است، برای آزمایش.")
        assert "این" not in tokens
        assert "است" not in tokens
        assert "،" not in tokens
        assert "نمونه" in tokens

    def test_repairs_persian_digit_words_consistently(self):

        assert tokenize("۲۰ واحد") == tokenize("۲۰ واحد")
