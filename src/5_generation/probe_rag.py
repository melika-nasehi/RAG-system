"""Run the full chain over questions chosen to expose different failure modes.

Retrieved passages are printed alongside each answer. An answer that reads
well can still be wrong, and the only way to tell is to see what it was
built from.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from rag_chain import RagChain

QUESTIONS = [
    # Answer is a specific number in one article — the easy case.
    "حداکثر تعداد واحد درسی در هر نیمسال چند است؟",
    # Answer spans several provisions across two documents.
    "شرایط استفاده از مرخصی تحصیلی چیست؟",
    # Small, topically isolated document.
    "برای استفاده از لوازم کوهنوردی چه شرایطی لازم است؟",
    # Colloquial phrasing against formal source wording — retrieval scored
    # poorly here, so the model should decline rather than improvise.
    "اگر سر کلاس نروم چه اتفاقی می‌افتد؟",
    # Not in the corpus at all. Retrieval still returns passages about
    # tuition; declining anyway is the behaviour under test.
    "شهریه دوره دکتری در سال ۱۴۰۴ چقدر است؟",
]


def main():
    chain = RagChain()

    for question in QUESTIONS:
        answer = chain.ask(question)

        print("=" * 70)
        print(f"Q: {question}")
        print("-" * 70)
        print(answer.text)

        print("\nretrieved:")
        for rank, passage in enumerate(answer.passages, start=1):
            snippet = " ".join(passage.text.split())[:80]
            print(f"  {rank}. {passage.score:.3f}  {passage.citation()}")
            print(f"     {snippet}...")

        print()


if __name__ == "__main__":
    main()