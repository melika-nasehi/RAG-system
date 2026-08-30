"""Measure Ollama embedding throughput call by call, not just averaged.

The first probe showed a huge spread (0.05s to 13.7s) on identical calls.
Printing each one separately shows whether that's warm-up cost or something
that recurs.
"""

import time

import ollama

MODEL = "qwen3-embedding:0.6b"

long_text = ("ماده ۱۷: انتخاب حداقل ۱۲ واحد درسی در هر نیمسال تحصیلی برای دانشجو الزامی است. " * 10)[:748]

print("warm-up call (discarded):")
start = time.time()
ollama.embed(model=MODEL, input=long_text)
print(f"  {time.time() - start:.2f}s\n")

print("ten steady-state calls, same text:")
for i in range(10):
    start = time.time()
    ollama.embed(model=MODEL, input=long_text)
    print(f"  call {i+1:2}: {time.time() - start:.2f}s")