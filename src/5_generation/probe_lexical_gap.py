"""Re-test the exact question that previously failed retrieval.

Q12/Q13 both hit on the first try, unlike the earlier probe where "اگر سر
کلاس نروم چه اتفاقی می‌افتد؟" (missing class) scored below 0.42 on every
candidate. That question was about class attendance, not exam absence — a
different regulation entirely. This checks whether that specific case still
fails now that the corpus includes two additional attendance-related
documents, or whether the lexical gap finding was a one-off.
"""

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