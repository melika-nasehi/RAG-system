"""Sanity-check source PDFs before they hit the pipeline."""

from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "calibration_data"

BLANK_PAGE_CHARS = 50

PERSIAN = re.compile(r'[\u0600-\u06FF]')
WHITESPACE = re.compile(r'\s')
PRINTABLE = re.compile(r'[^\x20-\x7E\u0600-\u06FF\u200c\s]')

# Font-mapping failures produce long alphanumeric runs like "afii62829".
# Real words in either language don't look like this.
GARBAGE_TOKEN = re.compile(r'\b[a-zA-Z]{2,}\d{2,}[a-zA-Z0-9]*\b')

# Arabic kaf/yeh look identical to the Persian ones but carry different
# codepoints, and NFKC won't merge them. Persian PDFs mix both freely.
ARABIC_TO_PERSIAN = str.maketrans({
    "\u0643": "\u06A9",  # kaf
    "\u064A": "\u06CC",  # yeh
    "\u0649": "\u06CC",  # alef maksura
    "\u0629": "\u0647",  # teh marbuta
})

# All markers are 5+ characters so a chance match inside garbled text is
# very unlikely. Matched as substrings against space-stripped text, because
# Persian PDFs frequently lose word-boundary spaces on extraction (e.g.
# "اهميتموضوع" instead of "اهميت موضوع") without the content being wrong.
#
# LIMITATION: tuned for administrative/regulatory Persian — bylaws,
# circulars, university documents. A text with none of this vocabulary
# (poetry, dialogue) could be flagged even when perfectly fine.
PERSIAN_MARKERS = [
    "دانشگاه", "آموزش", "تحصیلی", "دانشجو", "مصوب", "تبصره",
    "مقررات", "همچنین", "بنابراین", "براساس", "درصورت",
    "میشود", "هستند", "خواهد", "موظف", "مربوط",
]

NON_PERSIAN_CHAR = re.compile(r'[^\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]')


def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def normalize(text):
    folded = unicodedata.normalize("NFKC", text)
    return folded.translate(ARABIC_TO_PERSIAN)


def marker_hits(text):
    compact = NON_PERSIAN_CHAR.sub("", normalize(text))
    return sum(1 for marker in PERSIAN_MARKERS if marker in compact)


def page_marker_profile(pages):
    """Per-page marker counts, ignoring pages too short to judge.

    A document can be corrupt unevenly — headers extracted cleanly while the
    body is garbled. Scoring the whole document at once hides that.
    """
    scores = [
        marker_hits(p) for p in pages
        if len(p.strip()) >= BLANK_PAGE_CHARS
    ]
    if not scores:
        return {"scored_pages": 0, "pages_with_markers": 0, "marker_coverage": 0.0}

    with_markers = sum(1 for s in scores if s > 0)
    return {
        "scored_pages": len(scores),
        "pages_with_markers": with_markers,
        "marker_coverage": round(with_markers / len(scores) * 100, 1),
    }


def measure(pages):
    text = "\n".join(pages)
    dense = WHITESPACE.sub("", text)
    tokens = text.split()

    total = len(dense)
    if total == 0:
        return {
            "pages": len(pages),
            "chars": 0,
            "chars_per_page": 0,
            "blank_pages": len(pages),
            "persian_ratio": 0.0,
            "garbage_ratio": 0.0,
            "unknown_char_ratio": 0.0,
            "avg_token_length": 0.0,
            "marker_hits": 0,
            "scored_pages": 0,
            "pages_with_markers": 0,
            "marker_coverage": 0.0,
        }

    garbage = GARBAGE_TOKEN.findall(text)

    return {
        "pages": len(pages),
        "chars": total,
        "chars_per_page": total // len(pages),
        "blank_pages": sum(1 for p in pages if len(p.strip()) < BLANK_PAGE_CHARS),
        "persian_ratio": round(len(PERSIAN.findall(text)) / total * 100, 1),
        "garbage_ratio": round(len(garbage) / len(tokens) * 100, 1) if tokens else 0.0,
        "unknown_char_ratio": round(len(PRINTABLE.findall(text)) / total * 100, 1),
        "avg_token_length": round(sum(len(t) for t in tokens) / len(tokens), 1) if tokens else 0.0,
        "marker_hits": marker_hits(text),
        **page_marker_profile(pages),
    }


def main():
    pdfs = sorted(DATA_RAW_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs in {DATA_RAW_DIR}")
        return

    for pdf in pdfs:
        stats = measure(extract_pages(pdf))
        print(f"\n{pdf.name}")
        for key, value in stats.items():
            print(f"  {key:20} {value}")


if __name__ == "__main__":
    main()