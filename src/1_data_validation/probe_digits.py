"""How often do digit runs come out reversed in the accepted corpus?

Documents can pass vocabulary checks — their words are fine — while their
numbers are silently backwards. In a corpus of regulations, where the answer
to most questions is a number, that's the failure that matters most.
"""

from pathlib import Path
import re

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

# Three-part number groups. The middle part caps at two digits, which rules
# out letter references and long serial numbers.
DATE_LIKE = re.compile(
    r'([۰-۹0-9]{1,4})\s*[/-]\s*([۰-۹0-9]{1,2})\s*[/-]\s*([۰-۹0-9]{1,4})'
)

# Standalone four-digit runs, for the "۰۲ - ۰۳" academic-year style.
YEAR_LIKE = re.compile(r'(?<![۰-۹0-9])([۰-۹0-9]{4})(?![۰-۹0-9])')

JALALI_MIN = 1300
JALALI_MAX = 1450


def to_ascii(s):
    out = []
    for ch in s:
        cp = ord(ch)
        if 0x06F0 <= cp <= 0x06F9:
            out.append(str(cp - 0x06F0))
        elif 0x0660 <= cp <= 0x0669:
            out.append(str(cp - 0x0660))
        else:
            out.append(ch)
    return "".join(out)


def valid_date(a, b, c):
    return JALALI_MIN <= a <= JALALI_MAX and 1 <= b <= 12 and 1 <= c <= 31


def classify_date(parts):
    try:
        nums = [int(to_ascii(p)) for p in parts]
        rev = [int(to_ascii(p)[::-1]) for p in parts]
    except ValueError:
        return None

    forward = valid_date(*nums) or valid_date(*reversed(nums))
    backward = valid_date(*rev) or valid_date(*reversed(rev))

    if forward and backward:
        return "ambiguous"
    if forward:
        return "forward"
    if backward:
        return "reversed"
    return None


def classify_year(token):
    value = to_ascii(token)
    forward = JALALI_MIN <= int(value) <= JALALI_MAX
    backward = JALALI_MIN <= int(value[::-1]) <= JALALI_MAX

    if forward and backward:
        return "ambiguous"
    if forward:
        return "forward"
    if backward:
        return "reversed"
    return None


def profile(text):
    counts = {"forward": 0, "reversed": 0, "ambiguous": 0}

    for parts in DATE_LIKE.findall(text):
        verdict = classify_date(parts)
        if verdict:
            counts[verdict] += 1

    for token in YEAR_LIKE.findall(text):
        verdict = classify_year(token)
        if verdict:
            counts[verdict] += 1

    return counts


def main():
    for pdf in sorted(DATA_RAW_DIR.glob("*.pdf")):
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        counts = profile(text)
        total = counts["forward"] + counts["reversed"]

        share = counts["reversed"] / total * 100 if total else 0
        flag = "  <-- reversed" if share > 50 and total >= 3 else ""

        print(f"\n{pdf.name}")
        print(f"  forward {counts['forward']:4}  reversed {counts['reversed']:4}"
              f"  ambiguous {counts['ambiguous']:4}  ({share:.0f}% reversed){flag}")


if __name__ == "__main__":
    main()