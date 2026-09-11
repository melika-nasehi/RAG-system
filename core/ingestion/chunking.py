"""Split a PDF into chunk records ready for embedding.

Two repairs happen before splitting: hazm normalisation folds the Arabic and
Persian forms of the same letters together, and Persian digit runs are
reversed for files whose numerals came out backwards — but only where a date
test shows the file actually needs it, since reversing a correct file would
corrupt it.

Module form of src/2_chunking/chunk_documents.py. Chunk ids and record shape
match the existing chunk files exactly, so a document added here is
indistinguishable from one from the original offline run.
"""

from __future__ import annotations

from pathlib import Path
import re

from hazm import Normalizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100

# A chunk this short carries no usable context — usually a page-number
# fragment left at a page boundary.
MIN_CHUNK_LENGTH = 100

SEPARATORS = ["\n\n", "\n", "؟", ".", "،", " ", ""]

_PERSIAN_DIGIT_RUN = re.compile(r"[۰-۹]{2,}")
_DATE_LIKE = re.compile(r"([۰-۹0-9]{1,4})\s*[/-]\s*([۰-۹0-9]{1,2})\s*[/-]\s*([۰-۹0-9]{1,4})")
_YEAR_LIKE = re.compile(r"(?<![۰-۹0-9])([۰-۹]{4})(?![۰-۹0-9])")

_JALALI_MIN = 1300
_JALALI_MAX = 1450

_normalizer = Normalizer()


def collection_params(collection_name: str) -> tuple[int, int]:
    """('chunks_500_100') -> (500, 100). The chunk configuration is encoded
    in the collection name, so ingestion matches whatever the store holds."""
    parts = collection_name.split("_")
    try:
        return int(parts[-2]), int(parts[-1])
    except (IndexError, ValueError):
        return DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def _to_ascii(text: str) -> str:
    return "".join(
        str(ord(ch) - 0x06F0) if 0x06F0 <= ord(ch) <= 0x06F9 else ch for ch in text
    )


def _reverse_persian_digits(text: str) -> str:
    return _PERSIAN_DIGIT_RUN.sub(lambda m: m.group()[::-1], text)


def _count_valid_dates(text: str) -> int:
    hits = 0
    for parts in _DATE_LIKE.findall(text):
        try:
            a, b, c = (int(_to_ascii(part)) for part in parts)
        except ValueError:
            continue
        if (_JALALI_MIN <= a <= _JALALI_MAX and 1 <= b <= 12 and 1 <= c <= 31) or (
            _JALALI_MIN <= c <= _JALALI_MAX and 1 <= b <= 12 and 1 <= a <= 31
        ):
            hits += 1

    for token in _YEAR_LIKE.findall(text):
        if _JALALI_MIN <= int(_to_ascii(token)) <= _JALALI_MAX:
            hits += 1
    return hits


def _needs_digit_repair(text: str) -> bool:
    return _count_valid_dates(_reverse_persian_digits(text)) > _count_valid_dates(text)


def _load_document(pdf_path: Path) -> tuple[list[tuple[int, str]], bool]:
    reader = PdfReader(str(pdf_path))
    pages = [(n, page.extract_text() or "") for n, page in enumerate(reader.pages, start=1)]

    repair = _needs_digit_repair("\n".join(text for _, text in pages))

    prepared = []
    for number, text in pages:
        if not text.strip():
            continue
        if repair:
            text = _reverse_persian_digits(text)
        prepared.append((number, _normalizer.normalize(text)))
    return prepared, repair


def chunk_pdf(
    pdf_path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    source_name: str | None = None,
) -> list[dict]:
    """Chunk records for one PDF. `source_name` overrides the filename stored
    on each record and used to build its id (default: the file's own name)."""
    path = Path(pdf_path)
    name = source_name or path.name
    stem = Path(name).stem

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
    )

    pages, repaired = _load_document(path)

    chunks = []
    for page_number, text in pages:
        for position, piece in enumerate(splitter.split_text(text)):
            if len(piece) < MIN_CHUNK_LENGTH:
                continue
            chunks.append(
                {
                    "id": f"{stem}_p{page_number}_c{position}",
                    "text": piece,
                    "source": name,
                    "page": page_number,
                    "digits_repaired": repaired,
                }
            )
    return chunks
