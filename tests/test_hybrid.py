
import pytest

from core.retrieval.hybrid import HybridRetriever
from core.retrieval.retriever import Passage
from core.retrieval.sparse import SparseHit


def passage(chunk_id, score=0.5, source="سند.pdf", page=1):
    return Passage(
        text=f"متن {chunk_id}", source=source, page=page, score=score, chunk_id=chunk_id
    )


def hit(chunk_id, score=1.0, source="سند.pdf", page=1):
    return SparseHit(
        chunk_id=chunk_id, text=f"متن {chunk_id}", source=source, page=page, score=score
    )


class FakeDense:
    def __init__(self, passages):
        self._passages = passages

    def __len__(self):
        return len(self._passages)

    def search(self, question, top_k=4):
        return self._passages[:top_k]


class FakeSparse:
    def __init__(self, hits):
        self._hits = hits

    def search(self, question, top_k=4):
        return self._hits[:top_k]


def make_hybrid(dense_ids, sparse_ids, **kwargs):
    return HybridRetriever(
        dense=FakeDense([passage(i) for i in dense_ids]),
        sparse=FakeSparse([hit(i) for i in sparse_ids]),
        **kwargs,
    )


def test_agreement_between_retrievers_beats_a_single_top_hit():

    hybrid = make_hybrid(dense_ids=["A", "B", "C"], sparse_ids=["D", "B", "E"], rrf_k=1)
    ranked = [p.chunk_id for p in hybrid.search("q", top_k=3)]

    assert ranked[0] == "B"
    assert set(ranked[1:]) == {"A", "D"}


def test_result_is_capped_at_top_k():
    hybrid = make_hybrid(["A", "B", "C", "D"], ["E", "F", "G", "H"])
    assert len(hybrid.search("q", top_k=3)) == 3


def test_a_chunk_in_both_lists_appears_once():
    hybrid = make_hybrid(["A", "B"], ["B", "A"])
    ranked = [p.chunk_id for p in hybrid.search("q", top_k=10)]
    assert sorted(ranked) == ["A", "B"]


def test_results_are_ordered_by_descending_fused_score():
    hybrid = make_hybrid(["A", "B", "C"], ["A", "C", "B"])
    scores = [p.score for p in hybrid.search("q", top_k=3)]
    assert scores == sorted(scores, reverse=True)


def test_sparse_only_hit_still_becomes_a_passage_with_provenance():

    hybrid = HybridRetriever(
        dense=FakeDense([passage("A")]),
        sparse=FakeSparse([hit("Z", source="غیبت.pdf", page=4)]),
        rrf_k=1,
    )
    by_id = {p.chunk_id: p for p in hybrid.search("q", top_k=5)}

    assert "Z" in by_id
    assert by_id["Z"].source == "غیبت.pdf"
    assert by_id["Z"].page == 4
    assert by_id["Z"].citation() == "غیبت.pdf, صفحه 4"


def test_reported_score_is_the_fused_score_not_a_leftover():
    hybrid = make_hybrid(["A"], ["A"], rrf_k=60)
    result = hybrid.search("q", top_k=1)[0]
    # 1/(60+1) contributed twice
    assert result.score == pytest.approx(2 / 61, abs=1e-6)


def test_search_signature_matches_the_dense_retriever():

    hybrid = make_hybrid(["A", "B"], ["B", "C"])
    assert hybrid.search("q", top_k=2)
    assert hybrid.search("q") == hybrid.search("q", top_k=4)


@pytest.mark.integration
def test_real_hybrid_returns_ranked_passages_for_a_known_question():
    hybrid = HybridRetriever(collection_name="chunks_500_100")
    results = hybrid.search("مدت مجاز مرخصی زایمان چقدر است؟", top_k=4)

    assert len(results) == 4
    assert all(p.text and p.source.endswith(".pdf") for p in results)
    scores = [p.score for p in results]
    assert scores == sorted(scores, reverse=True)
