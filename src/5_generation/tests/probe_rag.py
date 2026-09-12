
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from rag_chain import RagChain

QUESTIONS = [
    "حداکثر تعداد واحد درسی در هر نیمسال چند است؟",
    "شرایط استفاده از مرخصی تحصیلی چیست؟",
    "برای استفاده از لوازم کوهنوردی چه شرایطی لازم است؟",
    "اگر سر کلاس نروم چه اتفاقی می‌افتد؟",
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