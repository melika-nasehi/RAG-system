

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from retriever import Retriever

QUESTIONS = [
    "حداکثر تعداد واحد درسی در هر نیمسال چند است؟",
    "شرایط استفاده از مرخصی تحصیلی چیست؟",
    "برای استفاده از لوازم کوهنوردی چه شرایطی لازم است؟",
    "اگر سر کلاس نروم چه اتفاقی می‌افتد؟",
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