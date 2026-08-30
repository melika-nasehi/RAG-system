"""Read the actual chunks, not just their statistics.

Chunk counts and mean sizes look fine long after a splitter has started
cutting mid-sentence or dropping the context a passage needs. The only way
to catch that is to read the output.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from chunk_documents import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    SEPARATORS,
    chunk_document,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET = BASE_DIR / "data" / "raw" / "education-7731-education1402-final.pdf"


def show_boundary(chunks, index):
    """Print two consecutive chunks so the overlap between them is visible."""
    first, second = chunks[index], chunks[index + 1]

    print(f"\n{'=' * 70}")
    print(f"chunk {index} — {first['source']} p{first['page']} — {len(first['text'])} chars")
    print(f"{'=' * 70}")
    print(first["text"])

    print(f"\n{'-' * 70}")
    print(f"chunk {index + 1} — p{second['page']} — {len(second['text'])} chars")
    print(f"{'-' * 70}")
    print(second["text"])

    tail = first["text"][-CHUNK_OVERLAP:]
    overlap_found = second["text"].startswith(tail[:50].strip()[:30])
    print(f"\noverlap carried over: {overlap_found}")


def main():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )

    chunks, repaired = chunk_document(TARGET, splitter)
    print(f"{len(chunks)} chunks, digits repaired: {repaired}")

    for index in (len(chunks) // 3, len(chunks) // 2):
        show_boundary(chunks, index)


if __name__ == "__main__":
    main()