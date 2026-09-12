

from pathlib import Path
import re

from hazm import Normalizer, SentenceTokenizer
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE = BASE_DIR / "data" / "question_candidates.md"

MIN_SENTENCE_LENGTH = 60
MAX_SENTENCE_LENGTH = 400

CANDIDATES_PER_DOCUMENT = 12

DIGITS = re.compile(r'[۰-۹0-9]')

CONSTRAINT_WORDS = [
    "حداکثر", "حداقل", "بیش از", "کمتر از", "موظف", "ممنوع",
    "مجاز", "الزامی", "نباید", "باید", "مشروط", "معادل",
]

DOT_LEADER = re.compile(r'(?:[.…]\s*){6,}')

MAX_DIGIT_DENSITY = 0.18

_normalizer = Normalizer()
_sentence_tokenizer = SentenceTokenizer()


def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    return [(n, p.extract_text() or "") for n, p in enumerate(reader.pages, start=1)]


def is_noise(sentence):
    if DOT_LEADER.search(sentence):
        return True

    return len(DIGITS.findall(sentence)) / len(sentence) > MAX_DIGIT_DENSITY


def score_sentence(sentence):
    """Higher means more likely to yield a question with one right answer."""
    digit_count = len(DIGITS.findall(sentence))
    constraint_count = sum(1 for word in CONSTRAINT_WORDS if word in sentence)

    if digit_count == 0 or constraint_count == 0:
        return 0

    return digit_count + constraint_count * 2


def find_candidates(pages, limit):
    scored = []

    for page_number, text in pages:
        normalized = _normalizer.normalize(text)

        for sentence in _sentence_tokenizer.tokenize(normalized):
            clean = " ".join(sentence.split())

            if not MIN_SENTENCE_LENGTH <= len(clean) <= MAX_SENTENCE_LENGTH:
                continue
            if is_noise(clean):
                continue

            score = score_sentence(clean)
            if score > 0:
                scored.append((score, page_number, clean))

    scored.sort(reverse=True, key=lambda item: item[0])
    return scored[:limit]


def main():
    pdfs = sorted(DATA_RAW_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {DATA_RAW_DIR}")
        return

    lines = [
        "# نامزدهای سوال ارزیابی\n\n",
        "> استخراج نیمه‌خودکار از متن اسناد. هر مورد باید توسط انسان بازبینی، ",
        "به سوال تبدیل، و جواب مرجع از متن سند استخراج شود.\n",
    ]

    total = 0
    for pdf in pdfs:
        candidates = find_candidates(extract_pages(pdf), CANDIDATES_PER_DOCUMENT)
        if not candidates:
            print(f"{pdf.name}: no candidates")
            continue

        lines.append(f"\n## {pdf.name}\n\n")
        for score, page, sentence in candidates:
            lines.append(f"- **[امتیاز {score} — صفحه {page}]** {sentence}\n")
            total += 1

        print(f"{pdf.name}: {len(candidates)} candidates")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("".join(lines), encoding="utf-8")
    print(f"\n{total} candidates written to {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()