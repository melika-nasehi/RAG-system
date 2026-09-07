"""The single place that knows how text becomes a vector in this project.

Qwen3-Embedding is asymmetric: passages are embedded as-is, queries carry an
instruction prefix. Measured on this corpus, the prefix widens the gap
between a relevant and an irrelevant passage from +0.404 to +0.423. Small,
but free.

Keeping both sides here means a change of model, prefix, or backend happens
in one file rather than wherever an encode call happened to be written.
"""

import ollama

MODEL_NAME = "qwen3-embedding:0.6b"
VECTOR_DIM = 1024

# The instruction Qwen3-Embedding was trained to see in front of a query.
# Documented in English by the model authors, who note that English wording
# works best even for non-English text.
QUERY_PREFIX = (
    "Instruct: Given a web search query, retrieve relevant passages "
    "that answer the query\nQuery:"
)


def embed_documents(texts):
    """Embed passages for storage. No prefix — this is the model's default."""
    response = ollama.embed(model=MODEL_NAME, input=texts)
    return response["embeddings"]


def embed_query(text):
    """Embed a user question for retrieval. Never call this on a passage."""
    response = ollama.embed(model=MODEL_NAME, input=QUERY_PREFIX + text)
    return response["embeddings"][0]


def health_check():
    """Confirm the model responds and returns the expected dimension.

    Worth doing before a long indexing run: a missing model surfaces here in
    a second rather than after a partial write.
    """
    vector = embed_query("تست")
    if len(vector) != VECTOR_DIM:
        raise RuntimeError(
            f"expected {VECTOR_DIM}-dim vectors from {MODEL_NAME}, "
            f"got {len(vector)}"
        )
    return True