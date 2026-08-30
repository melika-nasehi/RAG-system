"""Does memory grow across repeated encode calls?

Per-chunk time was increasing steadily (22.5s -> 26.5s) despite near-constant
input length, which points at accumulation rather than raw model cost.
"""

import gc
import time

import psutil
from sentence_transformers import SentenceTransformer

process = psutil.Process()

model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device="cpu")
model.max_seq_length = 512

text = "ماده ۱۷: انتخاب حداقل ۱۲ واحد درسی در هر نیمسال تحصیلی برای دانشجو الزامی است. " * 10
text = text[:748]

for i in range(10):
    start = time.time()
    model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    elapsed = time.time() - start

    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"call {i+1:2}  {elapsed:5.1f}s  memory: {mem_mb:7.1f} MB")