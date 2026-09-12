

import ollama

MODEL_NAME = "qwen3-embedding:0.6b"
VECTOR_DIM = 1024


QUERY_PREFIX = (
    "Instruct: Given a web search query, retrieve relevant passages "
    "that answer the query\nQuery:"
)


def embed_documents(texts):
    response = ollama.embed(model=MODEL_NAME, input=texts)
    return response["embeddings"]


def embed_query(text):
    response = ollama.embed(model=MODEL_NAME, input=QUERY_PREFIX + text)
    return response["embeddings"][0]


def health_check():

    vector = embed_query("تست")
    if len(vector) != VECTOR_DIM:
        raise RuntimeError(
            f"expected {VECTOR_DIM}-dim vectors from {MODEL_NAME}, "
            f"got {len(vector)}"
        )
    return True