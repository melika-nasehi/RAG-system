"""Surface passages likely to yield a checkable evaluation question.

Evaluating retrieval quality needs questions whose answers are already known,
and those answers have to come from the documents rather than from whoever is
writing the test — otherwise the system gets graded against answers derived
the same way it derives its own.

So this scans the corpus for sentences that state a rule with a definite
value, and proposes them. A human turns each one into a question and copies
the reference answer from the source. Nothing here writes either side.
"""

from pathlib import Path
import re

from hazm import Normalizer, SentenceTokenizer
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE = BASE_DIR / "data" / "question_candidates.md"

# Below this a sentence rarely carries a complete rule; above it, several
# rules run together and the reference answer stops being unambiguous.
MIN_SENTENCE_LENGTH = 60
MAX_SENTENCE_LENGTH = 400

CANDIDATES_PER_DOCUMENT = 12

DIGITS = re.compile(r'[۰-۹0-9]')

# Vocabulary marking a binding rule rather than description.
CONSTRAINT_WORDS = [
    "حداکثر", "حداقل", "بیش از", "کمتر از", "موظف", "ممنوع",
    "مجاز", "الزامی", "نباید", "باید", "مشروط", "معادل",
]

# Contents pages pair page numbers with rule vocabulary and score well
# despite carrying no content. What marks them is a long unbroken run of
# leader dots — a single "و …" inside a list of examples is ordinary prose.
DOT_LEADER = re.compile(r'(?:[.…]\s*){6,}')

# A rule states one or two values. Anything denser is a table that lost its
# column structure during extraction — the values survive but their labels
# don't, so the reference answer can't be trusted.
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

    # Constraint words weigh double: digits alone are as often a reference
    # number as a limit.
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