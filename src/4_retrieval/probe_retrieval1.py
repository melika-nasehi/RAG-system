from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from retriever import Retriever

r = Retriever()
for p in r.search("مهلت ارائه گواهی پزشکی برای حذف پزشکی چقدر است؟", top_k=5):
    print(f"{p.score:.3f}  {p.source}  p{p.page}")
    print(" ", p.text[:120])
    print()