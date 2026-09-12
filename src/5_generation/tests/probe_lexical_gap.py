
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "5_generation"))
from rag_chain import RagChain

chain = RagChain()
answer = chain.ask("اگر سر کلاس نروم چه اتفاقی می‌افتد؟")

print("ANSWER:")
print(answer.text)
print("\nRETRIEVED:")
for p in answer.passages:
    print(f"  {p.score:.3f}  {p.citation()}")
    print(f"    {' '.join(p.text.split())[:100]}...")