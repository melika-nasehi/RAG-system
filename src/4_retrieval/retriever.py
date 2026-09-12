
from dataclasses import dataclass
from pathlib import Path

import chromadb

from indexing.embedder import embed_query

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORE_DIR = BASE_DIR / "data" / "vector_store"

DEFAULT_COLLECTION = "chunks_500_100"

DEFAULT_TOP_K = 4

DEFAULT_CANDIDATES = 4


@dataclass(frozen=True)
class Passage:

    text: str
    source: str
    page: int
    score: float
    chunk_id: str

    def citation(self):
        return f"{self.source}, صفحه {self.page}"


class Retriever:
    def __init__(self, collection_name=DEFAULT_COLLECTION, store_dir=STORE_DIR):
        client = chromadb.PersistentClient(path=str(store_dir))
        self._collection = client.get_collection(collection_name)

    def __len__(self):
        return self._collection.count()

    def search(self, question, top_k=DEFAULT_TOP_K, candidates=None):
        pool_size = max(candidates or DEFAULT_CANDIDATES, top_k)

        results = self._collection.query(
            query_embeddings=[embed_query(question)],
            n_results=pool_size,
            include=["documents", "metadatas", "distances"],
        )

        passages = [
            Passage(
                text=document,
                source=metadata["source"],
                page=metadata["page"],
                score=round(1 - distance, 4),
                chunk_id=chunk_id,
            )
            for document, metadata, distance, chunk_id in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                results["ids"][0],
            )
        ]

        return passages[:top_k]