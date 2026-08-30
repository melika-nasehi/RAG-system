"""Read both suspect documents in full before deciding anything."""

from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

TARGETS = [
    "counsel-7166-hamyaran-salamat.pdf",
    "pgrad-8908-guidelines-incentivizing-top-performing-exceptionally-talented-students-pgrad.pdf",
]

for name in TARGETS:
    reader = PdfReader(DATA_RAW_DIR / name)
    print(f"\n{'#' * 70}\n# {name}\n{'#' * 70}")

    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        print(f"\n----- page {number} -----")
        print(text[:600])