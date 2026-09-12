

from pathlib import Path
import re

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET = BASE_DIR / "data" / "raw" / "education-7731-education1402-final.pdf"

PERSIAN_DIGIT_RUN = re.compile(r'[۰-۹]{2,}')

CONTEXT_WORDS = ["واحد", "ماده", "نمره", "نیمسال", "درصد", "سنوات", "حداکثر", "حداقل"]


def reverse_persian_digits(text):
    return PERSIAN_DIGIT_RUN.sub(lambda m: m.group()[::-1], text)


def main():
    text = "\n".join(p.extract_text() or "" for p in PdfReader(TARGET).pages)
    repaired = reverse_persian_digits(text)

    shown = 0
    for match in PERSIAN_DIGIT_RUN.finditer(text):
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)

        original = " ".join(text[start:end].split())
        if not any(word in original for word in CONTEXT_WORDS):
            continue

        fixed = " ".join(repaired[start:end].split())

        print(f"\nbefore: ...{original}...")
        print(f"after:  ...{fixed}...")

        shown += 1
        if shown >= 15:
            break


if __name__ == "__main__":
    main()