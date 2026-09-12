

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import pickle

from rank_bm25 import BM25Okapi

from core.retrieval.text import tokenize

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHUNKS_DIR = BASE_DIR / "data" / "chunks"
INDEX_DIR = BASE_DIR / "data" / "sparse_index"

_FORMAT_VERSION = 1


@dataclass(frozen=True)
class SparseHit:


    chunk_id: str
    text: str
    source: str
    page: int
    score: float


class SparseIndex:
    def __init__(self, records: list[dict], corpus_tokens: list[list[str]]):
        self._records = records
        self._bm25 = BM25Okapi(corpus_tokens)

    # ---- construction ----

    @classmethod
    def for_collection(cls, collection_name: str) -> "SparseIndex":

        return cls.load(CHUNKS_DIR / f"{collection_name}.jsonl")

    @classmethod
    def load(cls, chunks_file: Path) -> "SparseIndex":
        chunks_file = Path(chunks_file)
        if not chunks_file.exists():
            raise FileNotFoundError(f"chunk file not found: {chunks_file}")

        cache = INDEX_DIR / f"{chunks_file.stem}.pkl"
        signature = _signature(chunks_file)

        if cache.exists():
            try:
                stored = pickle.loads(cache.read_bytes())
                if stored.get("signature") == signature:
                    return cls(stored["records"], stored["corpus_tokens"])
            except (pickle.UnpicklingError, KeyError, EOFError):
                pass  # rebuild below

        records, corpus_tokens = _read_chunks(chunks_file)
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(
            pickle.dumps(
                {
                    "signature": signature,
                    "records": records,
                    "corpus_tokens": corpus_tokens,
                }
            )
        )
        return cls(records, corpus_tokens)

    # ---- query ----

    def __len__(self) -> int:
        return len(self._records)

    def search(self, question: str, top_k: int = 4) -> list[SparseHit]:

        scores = self._bm25.get_scores(tokenize(question))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        hits: list[SparseHit] = []
        for index in ranked[:top_k]:
            if scores[index] <= 0:
                break
            record = self._records[index]
            hits.append(
                SparseHit(
                    chunk_id=record["id"],
                    text=record["text"],
                    source=record["source"],
                    page=record["page"],
                    score=round(float(scores[index]), 4),
                )
            )
        return hits


def _signature(chunks_file: Path) -> tuple:
    stat = chunks_file.stat()
    return (_FORMAT_VERSION, chunks_file.name, stat.st_size, int(stat.st_mtime))


def _read_chunks(chunks_file: Path) -> tuple[list[dict], list[list[str]]]:
    records: list[dict] = []
    corpus_tokens: list[list[str]] = []
    with chunks_file.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            chunk = json.loads(line)
            records.append(
                {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                }
            )
            corpus_tokens.append(tokenize(chunk["text"]))
    return records, corpus_tokens
