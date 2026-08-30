"""Sanity-check source PDFs before they hit the pipeline.

Persian PDFs fail in several unrelated ways, and no single quality score
separates them. This measures the extracted text, tries the one repair that
proved out during calibration, and says whether the file is usable.
"""

from pathlib import Path
import re

from hazm import Normalizer, WordTokenizer, words_list
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

BLANK_PAGE_CHARS = 50

# Short tokens hit the 193k-entry vocabulary by chance far too often: garbled
# text scored 45% on 2-3 letter tokens and 0% once they were dropped.
MIN_TOKEN_LENGTH = 4

# Below this the ratio is noise rather than signal.
MIN_TOKENS_TO_JUDGE = 40

# Calibration set: clean documents landed at 58-65%, the one with broken
# intra-Persian font mapping at 39.7%. 50 sits in the gap.
MIN_VOCAB_RATIO = 50.0

# Reversing lifted one document from 10.5% to 43.8%. Anything smaller is
# noise, not evidence of a systematic problem.
REPAIR_MARGIN = 15.0

PERSIAN = re.compile(r'[\u0600-\u06FF]')
WHITESPACE = re.compile(r'\s')

# Font-mapping failures produce long alphanumeric runs like "afii62829".
# Real words in either language don't look like this.
GARBAGE_TOKEN = re.compile(r'\b[a-zA-Z]{2,}\d{2,}[a-zA-Z0-9]*\b')
MAX_GARBAGE_RATIO = 1.0

_normalizer = Normalizer()
_tokenizer = WordTokenizer()
_vocabulary = {entry[0] for entry in words_list()}


def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def vocab_score(text):
    """Share of substantial tokens that are real Persian words.

    Returns -1 when there's too little text to judge, so callers can tell
    "bad" apart from "unknown" instead of treating both as zero.
    """
    tokens = [
        t for t in _tokenizer.tokenize(_normalizer.normalize(text))
        if len(t) >= MIN_TOKEN_LENGTH
    ]
    if len(tokens) < MIN_TOKENS_TO_JUDGE:
        return -1.0

    known = sum(1 for t in tokens if t in _vocabulary)
    return round(known / len(tokens) * 100, 1)


def reverse_words(text):
    return " ".join(word[::-1] for word in text.split())


def diagnose(text):
    baseline = vocab_score(text)
    if baseline < 0:
        return {"vocab_raw": -1.0, "repair": "insufficient_text", "vocab_final": -1.0}

    reversed_score = vocab_score(reverse_words(text))
    if reversed_score - baseline >= REPAIR_MARGIN:
        return {"vocab_raw": baseline, "repair": "reverse_words", "vocab_final": reversed_score}

    return {"vocab_raw": baseline, "repair": "none", "vocab_final": baseline}


def verdict(stats):
    if stats["chars_per_page"] < 100:
        return "REJECT", "no extractable text"

    if stats["garbage_ratio"] > MAX_GARBAGE_RATIO:
        return "REJECT", "font mapped to latin placeholders"

    if stats["vocab_final"] < 0:
        return "REJECT", "too little text to judge"

    if stats["vocab_final"] < MIN_VOCAB_RATIO:
        return "REJECT", f"only {stats['vocab_final']}% real words"

    if stats["repair"] != "none":
        return "REPAIR", f"usable after {stats['repair']}"

    return "ACCEPT", "ok"


def measure(pages):
    text = "\n".join(pages)
    dense = WHITESPACE.sub("", text)
    raw_tokens = text.split()
    total = len(dense)

    if total == 0:
        return {
            "pages": len(pages),
            "chars": 0,
            "chars_per_page": 0,
            "blank_pages": len(pages),
            "persian_ratio": 0.0,
            "garbage_ratio": 0.0,
            "vocab_raw": -1.0,
            "repair": "no_text",
            "vocab_final": -1.0,
        }

    garbage = GARBAGE_TOKEN.findall(text)

    return {
        "pages": len(pages),
        "chars": total,
        "chars_per_page": total // len(pages),
        "blank_pages": sum(1 for p in pages if len(p.strip()) < BLANK_PAGE_CHARS),
        "persian_ratio": round(len(PERSIAN.findall(text)) / total * 100, 1),
        "garbage_ratio": round(len(garbage) / len(raw_tokens) * 100, 1) if raw_tokens else 0.0,
        **diagnose(text),
    }


def main():
    pdfs = sorted(DATA_RAW_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs in {DATA_RAW_DIR}")
        return

    for pdf in pdfs:
        print(f"\n{pdf.name}", flush=True)
        stats = measure(extract_pages(pdf))
        for key, value in stats.items():
            print(f"  {key:20} {value}")

        status, reason = verdict(stats)
        print(f"  -> {status}: {reason}")


if __name__ == "__main__":
    main()