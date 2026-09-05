from pathlib import Path
import sys
sys.path.insert(0, str(Path('src/5_generation')))
from rag_chain import RagChain

chain = RagChain()
for i in range(3):
    answer = chain.ask("برای انتقالی به دانشگاه دیگر چه شرایطی لازم است؟")
    print(f"--- attempt {i+1} ---")
    print(answer.text)
    print()