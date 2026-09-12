

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from core.indexing.build_index import add_chunks, remove_chunks
from core.ingestion.chunking import chunk_pdf, collection_params
from core.ingestion.validation import ValidationResult, validate_pdf
from core.retrieval.retriever import DEFAULT_COLLECTION
from core.retrieval.sparse import INDEX_DIR as SPARSE_INDEX_DIR

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHUNKS_DIR = BASE_DIR / "data" / "chunks"
RAW_DIR = BASE_DIR / "data" / "raw"


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    source: str
    reason: str
    chunks_added: int = 0
    chunks_total: int = 0
    digits_repaired: bool = False
    validation: ValidationResult | None = None


def ingest_pdf(pdf_path, collection_name: str = DEFAULT_COLLECTION) -> IngestResult:
    path = Path(pdf_path)
    source = path.name

    result = validate_pdf(path)
    if not result.accepted:
        return IngestResult(
            accepted=False,
            source=source,
            reason=result.reason,
            validation=result,
        )

    size, overlap = collection_params(collection_name)
    chunks = chunk_pdf(path, chunk_size=size, chunk_overlap=overlap, source_name=source)
    if not chunks:
        return IngestResult(
            accepted=False,
            source=source,
            reason="validation passed but no chunks met the minimum length",
            validation=result,
        )

    added = add_chunks(chunks, collection_name)
    _append_to_chunk_file(chunks, collection_name)

    return IngestResult(
        accepted=True,
        source=source,
        reason=result.reason,
        chunks_added=added,
        chunks_total=len(chunks),
        digits_repaired=chunks[0]["digits_repaired"],
        validation=result,
    )


def remove_document(source: str, collection_name: str = DEFAULT_COLLECTION) -> int:

    remove_chunks(source, collection_name)  # dense (Chroma)
    removed = _remove_from_chunk_file(source, collection_name)  # + sparse's input


    cache = SPARSE_INDEX_DIR / f"{collection_name}.pkl"
    cache.unlink(missing_ok=True)

    return removed


def _remove_from_chunk_file(source: str, collection_name: str) -> int:
    path = CHUNKS_DIR / f"{collection_name}.jsonl"
    if not path.exists():
        return 0

    kept = []
    removed = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            if json.loads(line)["source"] == source:
                removed += 1
            else:
                kept.append(line if line.endswith("\n") else line + "\n")

    if removed:
        path.write_text("".join(kept), encoding="utf-8")
    return removed


def _append_to_chunk_file(chunks: list[dict], collection_name: str) -> None:

    path = CHUNKS_DIR / f"{collection_name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    existing.add(json.loads(line)["id"])

    new = [chunk for chunk in chunks if chunk["id"] not in existing]
    if not new:
        return

    with path.open("a", encoding="utf-8") as handle:
        for chunk in new:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
