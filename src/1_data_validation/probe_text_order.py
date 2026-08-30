"""Which transformation makes a document's text read as real Persian?

Two documents in the corpus extract as valid Persian words in the wrong
order. One reverses the letters inside words, the other reverses the word
order within a line — different faults needing different fixes. Rather than
guess, apply each candidate and measure which one raises the share of
recognised words.
"""

from pathlib import Path

from hazm import Normalizer, WordTokenizer, words_list
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

MIN_TOKEN_LENGTH = 4

_normalizer = Normalizer()
_tokenizer = WordTokenizer()
_vocabulary = {entry[0] for entry in words_list()}


def vocab_score(text):
    tokens = [
        t for t in _tokenizer.tokenize(_normalizer.normalize(text))
        if len(t) >= MIN_TOKEN_LENGTH
    ]
    if len(tokens) < 40:
        return -1.0
    known = sum(1 for t in tokens if t in _vocabulary)
    return round(known / len(tokens) * 100, 1)


def reverse_letters(text):
    """Flip the characters inside each word, keeping word order."""
    return "\n".join(
        " ".join(word[::-1] for word in line.split())
        for line in text.split("\n")
    )


def reverse_word_order(text):
    """Flip the order of words in each line, keeping each word intact."""
    return "\n".join(
        " ".join(reversed(line.split()))
        for line in text.split("\n")
    )


def reverse_both(text):
    return reverse_word_order(reverse_letters(text))


TRANSFORMS = {
    "as_is": lambda t: t,
    "letters": reverse_letters,
    "word_order": reverse_word_order,
    "both": reverse_both,
}


def main():
    for pdf in sorted(DATA_RAW_DIR.glob("*.pdf")):
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        scores = {name: vocab_score(fn(text)) for name, fn in TRANSFORMS.items()}

        best = max(scores, key=scores.get)
        gain = scores[best] - scores["as_is"]
        flag = f"  <-- {best} (+{gain:.1f})" if gain >= 10 else ""

        print(f"\n{pdf.name}")
        print("  " + "  ".join(f"{k} {v:5}" for k, v in scores.items()) + flag)


if __name__ == "__main__":
    main()