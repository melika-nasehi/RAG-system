"""Split validated PDFs into chunks and write them out for embedding.

Two repairs happen before splitting. Text normalisation folds the Arabic and
Persian forms of the same letters together, and digit reversal fixes files
whose Persian numerals came out backwards — but only where a date test shows
the file actually needs it.

Output filenames carry the chunk parameters, so several configurations can
sit side by side and be compared once retrieval exists to measure them.
"""

import argparse
import json
from pathlib import Path
import re

from hazm import Normalizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
CHUNKS_DIR = BASE_DIR / "data" / "chunks"

DEFAULT_CHUNK_SIZE = 750
DEFAULT_CHUNK_OVERLAP = 200

# A chunk this short carries no usable context — usually a page-number
# fragment left over at a page boundary.
MIN_CHUNK_LENGTH = 100

# Tried in order; the splitter only falls through when a piece still exceeds
# the size limit.
SEPARATORS = ["\n\n", "\n", "؟", ".", "،", " ", ""]

PERSIAN_DIGIT_RUN = re.compile(r'[۰-۹]{2,}')
DATE_LIKE = re.compile(r'([۰-۹0-9]{1,4})\s*[/-]\s*([۰-۹0-9]{1,2})\s*[/-]\s*([۰-۹0-9]{1,4})')
YEAR_LIKE = re.compile(r'(?<![۰-۹0-9])([۰-۹]{4})(?![۰-۹0-9])')

JALALI_MIN = 1300
JALALI_MAX = 1450

_normalizer = Normalizer()


def to_ascii(s):
    return "".join(
        str(ord(ch) - 0x06F0) if 0x06F0 <= ord(ch) <= 0x06F9 else ch
        for ch in s
    )


def reverse_persian_digits(text):
    return PERSIAN_DIGIT_RUN.sub(lambda m: m.group()[::-1], text)


def count_valid_dates(text):
    hits = 0
    for parts in DATE_LIKE.findall(text):
        try:
            a, b, c = (int(to_ascii(p)) for p in parts)
        except ValueError:
            continue
        if (JALALI_MIN <= a <= JALALI_MAX and 1 <= b <= 12 and 1 <= c <= 31) or \
           (JALALI_MIN <= c <= JALALI_MAX and 1 <= b <= 12 and 1 <= a <= 31):
            hits += 1

    for token in YEAR_LIKE.findall(text):
        if JALALI_MIN <= int(to_ascii(token)) <= JALALI_MAX:
            hits += 1

    return hits


def needs_digit_repair(text):
    """Whether reversing Persian digits makes more dates parse.

    Applying the reversal unconditionally would corrupt files that were
    already correct, so it has to earn its way in per document.
    """
    return count_valid_dates(reverse_persian_digits(text)) > count_valid_dates(text)


def load_document(pdf_path):
    reader = PdfReader(pdf_path)
    pages = [(n, p.extract_text() or "") for n, p in enumerate(reader.pages, start=1)]

    repair = needs_digit_repair("\n".join(text for _, text in pages))

    prepared = []
    for number, text in pages:
        if not text.strip():
            continue
        if repair:
            text = reverse_persian_digits(text)
        prepared.append((number, _normalizer.normalize(text)))

    return prepared, repair


def chunk_document(pdf_path, splitter):
    pages, repaired = load_document(pdf_path)

    chunks = []
    for page_number, text in pages:
        for position, piece in enumerate(splitter.split_text(text)):
            if len(piece) < MIN_CHUNK_LENGTH:
                continue
            chunks.append({
                "id": f"{pdf_path.stem}_p{page_number}_c{position}",
                "text": piece,
                "source": pdf_path.name,
                "page": page_number,
                "digits_repaired": repaired,
            })

    return chunks, repaired


def build(chunk_size, chunk_overlap):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
    )

    all_chunks = []
    for pdf in sorted(DATA_RAW_DIR.glob("*.pdf")):
        chunks, repaired = chunk_document(pdf, splitter)
        all_chunks.extend(chunks)
        note = "  (digits reversed)" if repaired else ""
        print(f"{pdf.name}: {len(chunks)} chunks{note}", flush=True)

    return all_chunks


def write(chunks, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    args = parser.parse_args()

    chunks = build(args.size, args.overlap)
    output = CHUNKS_DIR / f"chunks_{args.size}_{args.overlap}.jsonl"
    write(chunks, output)

    sizes = [len(c["text"]) for c in chunks]
    print(f"\nchunk size {args.size}, overlap {args.overlap}")
    print(f"  total      {len(chunks)}")
    print(f"  mean       {sum(sizes) // len(sizes)}")
    print(f"  min / max  {min(sizes)} / {max(sizes)}")
    print(f"  written to {output.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()