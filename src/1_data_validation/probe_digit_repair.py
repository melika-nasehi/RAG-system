"""Does reversing Persian digit runs make a document's dates parse?

Some exports lay out Persian-Indic digits in visual order, so ۱۴۰۳ comes
back as ۳۰۴۱. Latin digits in the same file survive intact, which is the
clue: the fix has to target one and leave the other alone.

Applying it blindly would corrupt files that were fine. So this measures how
many dates parse before and after, and only a clear gain counts as evidence.
"""

from pathlib import Path
import re

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

PERSIAN_DIGIT_RUN = re.compile(r'[۰-۹]{2,}')

DATE_LIKE = re.compile(
    r'([۰-۹0-9]{1,4})\s*[/-]\s*([۰-۹0-9]{1,2})\s*[/-]\s*([۰-۹0-9]{1,4})'
)
YEAR_LIKE = re.compile(r'(?<![۰-۹0-9])([۰-۹]{4})(?![۰-۹0-9])')

JALALI_MIN = 1300
JALALI_MAX = 1450


def to_ascii(s):
    return "".join(
        str(ord(ch) - 0x06F0) if 0x06F0 <= ord(ch) <= 0x06F9 else ch
        for ch in s
    )


def reverse_persian_digits(text):
    """Flip Persian digit runs, leaving Latin digits and letters untouched."""
    return PERSIAN_DIGIT_RUN.sub(lambda m: m.group()[::-1], text)


def valid_date(a, b, c):
    return JALALI_MIN <= a <= JALALI_MAX and 1 <= b <= 12 and 1 <= c <= 31


def count_valid(text):
    """Dates that parse as real Jalali dates, either ordering."""
    hits = 0

    for parts in DATE_LIKE.findall(text):
        try:
            nums = [int(to_ascii(p)) for p in parts]
        except ValueError:
            continue
        if valid_date(*nums) or valid_date(*reversed(nums)):
            hits += 1

    for token in YEAR_LIKE.findall(text):
        if JALALI_MIN <= int(to_ascii(token)) <= JALALI_MAX:
            hits += 1

    return hits


def main():
    for pdf in sorted(DATA_RAW_DIR.glob("*.pdf")):
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)

        before = count_valid(text)
        after = count_valid(reverse_persian_digits(text))

        if before == 0 and after == 0:
            note = "no dates found"
        elif after > before:
            note = "REPAIR: reversing helps"
        elif after < before:
            note = "leave alone: reversing breaks it"
        else:
            note = "no change"

        print(f"\n{pdf.name}")
        print(f"  valid dates  before {before:3}  after {after:3}   {note}")


if __name__ == "__main__":
    main()