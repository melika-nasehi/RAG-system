"""Diagnostic: is the Persian text in these PDFs stored in logical order?

Some producers emit Arabic Presentation Forms in visual order. Letters still
read fine, but digit runs come out reversed — 1393/12/16 becomes 3931/21/61.
That fails silently, so we look for two independent signals: date patterns
that only validate when reversed, and whether common Persian words survive
normalisation at all.
"""

from collections import Counter
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
CALIBRATION_DIR = BASE_DIR / "data" / "calibration_data"

DATE_PATTERN = re.compile(r'([\u0660-\u0669\u06F0-\u06F9\d]{1,4})/([\u0660-\u0669\u06F0-\u06F9\d]{1,2})/([\u0660-\u0669\u06F0-\u06F9\d]{1,4})')

# Frequent enough that a Persian document without them is suspect.
COMMON_WORDS = ["است", "این", "که", "از", "در", "ماده", "تبصره", "می", "را", "به"]

JALALI_MIN_YEAR = 1300
JALALI_MAX_YEAR = 1450


def to_ascii_digits(s):
    out = []
    for ch in s:
        cp = ord(ch)
        if 0x0660 <= cp <= 0x0669:
            out.append(str(cp - 0x0660))
        elif 0x06F0 <= cp <= 0x06F9:
            out.append(str(cp - 0x06F0))
        else:
            out.append(ch)
    return "".join(out)


def is_valid_jalali(year, month, day):
    return (
        JALALI_MIN_YEAR <= year <= JALALI_MAX_YEAR
        and 1 <= month <= 12
        and 1 <= day <= 31
    )


def check_date(parts):
    """Try a three-part number group as a date, forwards and reversed.

    Returns 'forward', 'reversed', 'both' or None. Iranian dates appear as
    year/month/day and day/month/year, so both orderings are tried.
    """
    try:
        a, b, c = (int(to_ascii_digits(p)) for p in parts)
    except ValueError:
        return None

    forward = is_valid_jalali(a, b, c) or is_valid_jalali(c, b, a)

    ra, rb, rc = (int(to_ascii_digits(p)[::-1]) for p in parts)
    backward = is_valid_jalali(ra, rb, rc) or is_valid_jalali(rc, rb, ra)

    if forward and backward:
        return "both"
    if forward:
        return "forward"
    if backward:
        return "reversed"
    return None


def classify_block(ch):
    cp = ord(ch)
    if 0x0600 <= cp <= 0x06FF:
        return "arabic_base"
    if 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
        return "presentation"
    if 0x20 <= cp <= 0x7E:
        return "ascii"
    return "other"


def probe(pdf_path):
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
    dense = [c for c in text if not c.isspace()]

    if not dense:
        return None

    blocks = Counter(classify_block(c) for c in dense)
    persian = blocks["arabic_base"] + blocks["presentation"]

    verdicts = Counter(
        v for v in (check_date(m) for m in DATE_PATTERN.findall(text)) if v
    )

    # NFKC folds presentation forms back to base letters, so word matching
    # works on either encoding.
    folded = unicodedata.normalize("NFKC", text)
    word_hits = sum(folded.count(w) for w in COMMON_WORDS)

    return {
        "chars": len(dense),
        "presentation_share": round(blocks["presentation"] / persian * 100, 1) if persian else 0.0,
        "dates_forward": verdicts["forward"],
        "dates_reversed": verdicts["reversed"],
        "dates_ambiguous": verdicts["both"],
        "common_words": word_hits,
    }


def main():
    for pdf in sorted(CALIBRATION_DIR.glob("*.pdf")):
        result = probe(pdf)

        print(f"\n{pdf.name}")
        if result is None:
            print("  no extractable text")
            continue

        for key, value in result.items():
            print(f"  {key:20} {value}")


if __name__ == "__main__":
    main()