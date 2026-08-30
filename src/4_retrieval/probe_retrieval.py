"""Look at what retrieval returns for a spread of question types.

Reading the output matters more than any single number here: a passage can
score well and still not answer the question, and that only shows up on
inspection.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from retriever import Retriever

QUESTIONS = [
    # Answer is a specific number in one article.
    "حداکثر تعداد واحد درسی در هر نیمسال چند است؟",
    # Answer spans several provisions.
    "شرایط استفاده از مرخصی تحصیلی چیست؟",
    # Answer lives in a small, topically distinct document.
    "برای استفاده از لوازم کوهنوردی چه شرایطی لازم است؟",
    # Phrased differently from how the documents word it.
    "اگر سر کلاس نروم چه اتفاقی می‌افتد؟",
    # Nothing in the corpus answers this.
    "شهریه دوره دکتری در سال ۱۴۰۴ چقدر است؟",
]


def main():
    retriever = Retriever()
    print(f"collection holds {len(retriever)} passages\n")

    for question in QUESTIONS:
        print(f"Q: {question}")

        for rank, passage in enumerate(retriever.search(question), start=1):
            snippet = " ".join(passage.text.split())[:110]
            print(f"  {rank}. {passage.score:.3f}  {passage.citation()}")
            print(f"     {snippet}...")

        print()


if __name__ == "__main__":
    main()