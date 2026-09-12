

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from hazm import Normalizer, WordTokenizer, words_list
from pypdf import PdfReader

BLANK_PAGE_CHARS = 50

MIN_TOKEN_LENGTH = 4
MIN_TOKENS_TO_JUDGE = 40

MIN_VOCAB_RATIO = 50.0

REPAIR_MARGIN = 15.0

MIN_CHARS_PER_PAGE = 100

GARBAGE_TOKEN = re.compile(r"\b[a-zA-Z]{2,}\d{2,}[a-zA-Z0-9]*\b")
MAX_GARBAGE_RATIO = 1.0

_PERSIAN = re.compile(r"[؀-ۿ]")
_WHITESPACE = re.compile(r"\s")

_normalizer = Normalizer()
_tokenizer = WordTokenizer()
_vocabulary = {entry[0] for entry in words_list()}


@dataclass(frozen=True)
class ValidationResult:


    accepted: bool
    verdict: str  # "ACCEPT" | "REPAIR" | "REJECT"
    reason: str
    stats: dict = field(default_factory=dict)


def validate_pdf(pdf_path) -> ValidationResult:
    path = Path(pdf_path)
    try:
        pages = _extract_pages(path)
    except Exception as error:  # pypdf raises a zoo of exception types
        return ValidationResult(False, "REJECT", f"unreadable PDF: {error}", {})

    stats = _measure(pages)
    verdict, reason = _verdict(stats)
    return ValidationResult(verdict != "REJECT", verdict, reason, stats)


def _extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def _vocab_score(text: str) -> float:

    tokens = [
        token
        for token in _tokenizer.tokenize(_normalizer.normalize(text))
        if len(token) >= MIN_TOKEN_LENGTH
    ]
    if len(tokens) < MIN_TOKENS_TO_JUDGE:
        return -1.0

    known = sum(1 for token in tokens if token in _vocabulary)
    return round(known / len(tokens) * 100, 1)


def _reverse_words(text: str) -> str:
    return " ".join(word[::-1] for word in text.split())


def _diagnose(text: str) -> dict:
    baseline = _vocab_score(text)
    if baseline < 0:
        return {"vocab_raw": -1.0, "repair": "insufficient_text", "vocab_final": -1.0}

    reversed_score = _vocab_score(_reverse_words(text))
    if reversed_score - baseline >= REPAIR_MARGIN:
        return {"vocab_raw": baseline, "repair": "reverse_words", "vocab_final": reversed_score}

    return {"vocab_raw": baseline, "repair": "none", "vocab_final": baseline}


def _measure(pages: list[str]) -> dict:
    text = "\n".join(pages)
    dense = _WHITESPACE.sub("", text)
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
        "chars_per_page": total // max(len(pages), 1),
        "blank_pages": sum(1 for page in pages if len(page.strip()) < BLANK_PAGE_CHARS),
        "persian_ratio": round(len(_PERSIAN.findall(text)) / total * 100, 1),
        "garbage_ratio": round(len(garbage) / len(raw_tokens) * 100, 1) if raw_tokens else 0.0,
        **_diagnose(text),
    }


def _verdict(stats: dict) -> tuple[str, str]:
    if stats["chars_per_page"] < MIN_CHARS_PER_PAGE:
        return "REJECT", "no extractable text (scanned or image-only PDF)"
    if stats["garbage_ratio"] > MAX_GARBAGE_RATIO:
        return "REJECT", "font mapped to Latin placeholders — text is not recoverable"
    if stats["vocab_final"] < 0:
        return "REJECT", "too little Persian text to judge"
    if stats["vocab_final"] < MIN_VOCAB_RATIO:
        return "REJECT", f"only {stats['vocab_final']}% of tokens are real Persian words"
    if stats["repair"] != "none":
        return "REPAIR", f"usable after {stats['repair']}"
    return "ACCEPT", "ok"
