"""Unit tests for the ingestion pipeline (validate -> chunk -> index).

Validation and chunking run against the real PDFs in data/raw — they are
local and fast, and the whole point is that the acceptance rules behave on
actual documents. Only the embedding/indexing step is stubbed, since that
needs Ollama and a Chroma write.
"""

import json
from pathlib import Path

import pytest

from core.ingestion import pipeline as pipeline_module
from core.ingestion.chunking import chunk_pdf, collection_params
from core.ingestion.pipeline import ingest_pdf, remove_document
from core.ingestion.validation import validate_pdf

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"


@pytest.fixture(scope="module")
def a_real_pdf():
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip("no source PDFs in data/raw")
    return pdfs[0]


# ---- validation ----

def test_accepts_a_real_regulation_pdf(a_real_pdf):
    result = validate_pdf(a_real_pdf)
    assert result.accepted
    assert result.verdict in {"ACCEPT", "REPAIR"}


def test_rejects_a_non_pdf_file(tmp_path):
    fake = tmp_path / "notreal.pdf"
    fake.write_text("this is plain text, not a PDF", encoding="utf-8")

    result = validate_pdf(fake)
    assert not result.accepted
    assert result.verdict == "REJECT"
    assert "PDF" in result.reason or "pdf" in result.reason


def test_rejects_an_empty_pdf(tmp_path):
    fake = tmp_path / "empty.pdf"
    fake.write_bytes(b"")

    result = validate_pdf(fake)
    assert not result.accepted


# ---- chunking ----

def test_collection_params_parses_the_name():
    assert collection_params("chunks_500_100") == (500, 100)
    assert collection_params("chunks_1000_200") == (1000, 200)


def test_chunk_records_have_the_expected_shape(a_real_pdf):
    chunks = chunk_pdf(a_real_pdf, chunk_size=500, chunk_overlap=100)
    assert chunks

    first = chunks[0]
    assert set(first) == {"id", "text", "source", "page", "digits_repaired"}
    assert first["source"] == a_real_pdf.name
    assert first["id"].startswith(a_real_pdf.stem)
    assert first["page"] >= 1
    assert all(len(c["text"]) >= 100 for c in chunks)


def test_source_name_override_drives_the_id(a_real_pdf):
    chunks = chunk_pdf(a_real_pdf, source_name="renamed.pdf")
    assert chunks[0]["source"] == "renamed.pdf"
    assert chunks[0]["id"].startswith("renamed_p")


# ---- pipeline ----

def test_pipeline_rejects_before_indexing(tmp_path, monkeypatch):
    """A file that fails validation must never reach the indexer."""
    calls = []
    monkeypatch.setattr(pipeline_module, "add_chunks", lambda *a, **k: calls.append(a))

    fake = tmp_path / "broken.pdf"
    fake.write_text("not a pdf", encoding="utf-8")

    result = ingest_pdf(fake)
    assert result.accepted is False
    assert result.chunks_added == 0
    assert calls == []


def test_pipeline_indexes_and_appends_on_accept(a_real_pdf, tmp_path, monkeypatch):
    added = {}
    monkeypatch.setattr(
        pipeline_module, "add_chunks",
        lambda chunks, name, **k: added.setdefault(name, len(chunks)) or len(chunks),
    )
    monkeypatch.setattr(pipeline_module, "CHUNKS_DIR", tmp_path)

    result = ingest_pdf(a_real_pdf, collection_name="chunks_500_100")

    assert result.accepted
    assert result.chunks_total > 0
    assert added["chunks_500_100"] == result.chunks_total

    chunk_file = tmp_path / "chunks_500_100.jsonl"
    assert chunk_file.exists()
    assert sum(1 for _ in chunk_file.open(encoding="utf-8")) == result.chunks_total

    # Re-running must not duplicate lines in the chunk file.
    ingest_pdf(a_real_pdf, collection_name="chunks_500_100")
    assert sum(1 for _ in chunk_file.open(encoding="utf-8")) == result.chunks_total


# ---- removal ----

def _write_chunk_file(path, records):
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def test_remove_document_deletes_only_its_own_lines(tmp_path, monkeypatch):
    chunk_file = tmp_path / "chunks_500_100.jsonl"
    _write_chunk_file(
        chunk_file,
        [
            {"id": "keep_p1_c0", "text": "x" * 120, "source": "keep.pdf", "page": 1},
            {"id": "gone_p1_c0", "text": "y" * 120, "source": "gone.pdf", "page": 1},
            {"id": "gone_p2_c0", "text": "z" * 120, "source": "gone.pdf", "page": 2},
        ],
    )
    monkeypatch.setattr(pipeline_module, "CHUNKS_DIR", tmp_path)
    monkeypatch.setattr(pipeline_module, "SPARSE_INDEX_DIR", tmp_path)

    dense_calls = []
    monkeypatch.setattr(
        pipeline_module, "remove_chunks",
        lambda source, name: dense_calls.append((source, name)),
    )

    removed = remove_document("gone.pdf", collection_name="chunks_500_100")

    assert removed == 2
    assert dense_calls == [("gone.pdf", "chunks_500_100")]  # dense index was told too
    remaining = [json.loads(line) for line in chunk_file.open(encoding="utf-8")]
    assert [c["source"] for c in remaining] == ["keep.pdf"]


def test_remove_document_makes_the_sparse_index_stop_finding_it(tmp_path, monkeypatch):
    """The specific regression this is guarding against: the sparse index is
    a pickled cache keyed on the chunk file's (size, mtime). If removal
    rewrote the chunk file but the stale .pkl survived, a query that used to
    match only the deleted document would keep matching it forever. This
    goes through the real SparseIndex, not a mock, to prove the cache
    actually gets invalidated end to end."""
    from core.retrieval import sparse as sparse_module
    from core.retrieval.sparse import SparseIndex

    # A collection name distinct from any real one, and the sparse cache
    # directory pointed at tmp_path too — otherwise SparseIndex.load()'s own
    # cache (keyed only by filename, from its module-level INDEX_DIR) would
    # read or write the real project's data/sparse_index/, not this test's.
    collection_name = "test_remove_doc_sparse"
    chunk_file = tmp_path / f"{collection_name}.jsonl"
    _write_chunk_file(
        chunk_file,
        [
            {
                "id": "unique_p1_c0",
                "text": "استفاده از زردچوبه در آشپزی دانشجویی مجاز است " * 3,
                "source": "unique.pdf",
                "page": 1,
            },
            # Two unrelated documents, so the query term sits in a strict
            # minority of the corpus (1 of 3) — with it in exactly half
            # (1 of 2), rank_bm25's IDF term lands on precisely zero, an
            # edge case of the *test's* tiny corpus, not of remove_document.
            {
                "id": "other_p1_c0",
                "text": "مقررات عمومی ثبت‌نام و انتخاب واحد دانشجویان " * 3,
                "source": "other.pdf",
                "page": 1,
            },
            {
                "id": "other2_p1_c0",
                "text": "شرایط اعطای وام تحصیلی و بازپرداخت اقساط " * 3,
                "source": "other.pdf",
                "page": 2,
            },
        ],
    )
    monkeypatch.setattr(pipeline_module, "CHUNKS_DIR", tmp_path)
    monkeypatch.setattr(pipeline_module, "SPARSE_INDEX_DIR", tmp_path)
    monkeypatch.setattr(sparse_module, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(pipeline_module, "remove_chunks", lambda *a, **k: None)  # dense: not under test here

    before = SparseIndex.load(chunk_file).search("زردچوبه آشپزی", top_k=4)
    assert any(hit.chunk_id == "unique_p1_c0" for hit in before)

    remove_document("unique.pdf", collection_name=collection_name)

    after = SparseIndex.load(chunk_file).search("زردچوبه آشپزی", top_k=4)
    assert after == []


def test_remove_document_for_a_source_not_present_is_a_safe_noop(tmp_path, monkeypatch):
    chunk_file = tmp_path / "chunks_500_100.jsonl"
    _write_chunk_file(
        chunk_file, [{"id": "a", "text": "x" * 120, "source": "keep.pdf", "page": 1}]
    )
    monkeypatch.setattr(pipeline_module, "CHUNKS_DIR", tmp_path)
    monkeypatch.setattr(pipeline_module, "SPARSE_INDEX_DIR", tmp_path)
    monkeypatch.setattr(pipeline_module, "remove_chunks", lambda *a, **k: None)

    removed = remove_document("never-uploaded.pdf", collection_name="chunks_500_100")

    assert removed == 0
    remaining = [json.loads(line) for line in chunk_file.open(encoding="utf-8")]
    assert [c["source"] for c in remaining] == ["keep.pdf"]
