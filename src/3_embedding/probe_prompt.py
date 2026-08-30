"""Does the query instruction still matter when going through Ollama?

sentence-transformers applies Qwen3's query prefix via prompt_name. Ollama's
API takes a bare input string, so either it applies the prefix internally or
it doesn't apply one at all — and getting that wrong degrades retrieval
without raising anything.
"""

import ollama

MODEL = "qwen3-embedding:0.6b"

# The prefix sentence-transformers reports for this model's "query" prompt.
QUERY_PREFIX = (
    "Instruct: Given a web search query, retrieve relevant passages "
    "that answer the query\nQuery:"
)

question = "حداکثر تعداد واحد مجاز در یک نیمسال چند است؟"

passages = [
    "ماده ۱۷: انتخاب حداقل ۱۲ واحد درسی در هر نیمسال تحصیلی برای دانشجو الزامی است. حداکثر واحد درسی قابل اخذ در هر نیمسال تحصیلی ۲۰ واحد است.",
    "ماده ۵: دانشجو موظف است سوابق مرتبط با استفاده از هوش مصنوعی را تا پایان فرایند داوری نگهداری نماید.",
]


def embed(text):
    return ollama.embed(model=MODEL, input=text)["embeddings"][0]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b)


passage_vectors = [embed(p) for p in passages]

for label, query_text in [
    ("without prefix", question),
    ("with prefix", QUERY_PREFIX + question),
]:
    query_vector = embed(query_text)
    scores = [cosine(query_vector, pv) for pv in passage_vectors]

    print(f"\n{label}")
    print(f"  relevant passage:   {scores[0]:.4f}")
    print(f"  irrelevant passage: {scores[1]:.4f}")
    print(f"  gap:                {scores[0] - scores[1]:+.4f}")