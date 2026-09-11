"""Unit tests for the embedding layer.

These tests hit the real Ollama model rather than mocking it, because the
one thing worth verifying here — the asymmetric query/document behaviour —
only shows up in the actual model's output. A mock would just test that we
call the mock correctly.
"""

import pytest

from core.indexing.embedder import embed_documents, embed_query, health_check, VECTOR_DIM


def test_health_check_passes():
    """Confirms Ollama is reachable and the model returns the expected shape."""
    assert health_check() is True


def test_query_vector_has_correct_dimension():
    vector = embed_query("حداکثر واحد درسی چند است؟")
    assert len(vector) == VECTOR_DIM


def test_document_vectors_have_correct_dimension():
    vectors = embed_documents(["متن نمونه یک", "متن نمونه دو"])
    assert len(vectors) == 2
    assert all(len(v) == VECTOR_DIM for v in vectors)


def test_query_prefix_changes_the_vector():
    """A query and the same text embedded as a document should differ,
    since the query path prepends an instruction prefix. If this test ever
    fails, someone has broken the asymmetric encoding that section 11.2 of
    the notes found necessary for correct ranking."""
    text = "شرایط مرخصی تحصیلی"

    as_query = embed_query(text)
    as_document = embed_documents([text])[0]

    assert as_query != as_document


def test_relevant_passage_scores_higher_than_irrelevant():
    """Reproduces the core sanity check from the embedding validation phase:
    a query should be closer to a relevant passage than an irrelevant one."""
    query = embed_query("حداکثر تعداد واحد درسی در هر نیمسال چند است؟")

    relevant = embed_documents([
        "ماده ۱۷: انتخاب حداقل ۱۲ واحد درسی در هر نیمسال تحصیلی الزامی است."
    ])[0]
    irrelevant = embed_documents([
        "شرایط استفاده از خوابگاه دانشجویی و مقررات انضباطی آن"
    ])[0]

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        return dot / (norm_a * norm_b)

    assert cosine(query, relevant) > cosine(query, irrelevant)