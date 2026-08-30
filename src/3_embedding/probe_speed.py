"""Where is the time actually going?

Two hours for 452 short passages on a 0.6B model suggests something other
than raw model size — likely thread configuration or a per-call overhead
that dominates at this scale.
"""

import time

import torch
from sentence_transformers import SentenceTransformer

print(f"torch threads: {torch.get_num_threads()}")
print(f"cpu count: {torch.get_num_interop_threads()} interop")

model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device="cpu")

short = "حداکثر تعداد واحد مجاز چند است؟"
long = "ماده ۱۷: انتخاب حداقل ۱۲ واحد درسی در هر نیمسال تحصیلی برای دانشجو الزامی است. " * 6

for label, text, count in [("short x1", short, 1), ("long x1", long, 1),
                           ("short x8", short, 8), ("long x8", long, 8)]:
    batch = [text] * count
    start = time.time()
    model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
    elapsed = time.time() - start
    print(f"  {label:10} {len(text):5} chars  {elapsed:6.2f}s  ({elapsed/count:.2f}s each)")