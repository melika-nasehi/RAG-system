
from sentence_transformers import SentenceTransformer

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

print(f"loading {MODEL_NAME} ...", flush=True)
model = SentenceTransformer(MODEL_NAME, device="cpu")
print("loaded", flush=True)
print("available prompts:", model.prompts, flush=True)

query = "حداکثر تعداد واحد مجاز در یک نیمسال چند است؟"

documents = [
    "سقف واحدهای درسی قابل اخذ در هر ترم",       # relevant
    "شرایط استفاده از خوابگاه دانشجویی",           # irrelevant
]

query_vec = model.encode(query, prompt_name="query", normalize_embeddings=True)
doc_vecs = model.encode(documents, normalize_embeddings=True)

print(f"\nquery: {query}")
for doc, vec in zip(documents, doc_vecs):
    score = float(query_vec @ vec)
    print(f"  {score:.3f}  {doc}")