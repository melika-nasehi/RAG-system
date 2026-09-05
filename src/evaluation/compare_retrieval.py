"""Compare chunking configurations on retrieval quality alone.

Chunk size mainly affects what gets retrieved, not how well the model writes
from it — so the choice can be made on retrieval metrics without paying for
generation. That matters here: a full three-way comparison through the LLM
is 48 calls, which either exhausts a free-tier quota or takes hours locally.
Measuring retrieval directly costs neither.

Two metrics, because they answer different questions:
- hit rate: was the right document retrieved at all?
- rank of first hit: how far down was it? A hit at position 1 is worth more
  than a hit at position 4, since the generator sees a fixed top-k window.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "4_retrieval"))
from retriever import Retriever

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"

CONFIGURATIONS = [
    "chunks_500_100",
    "chunks_750_200",
    "chunks_1000_200",
]

# Wider than the generator's window, so a document retrieved just outside
# the top-k still shows up in the rank statistics rather than vanishing.
SEARCH_DEPTH = 10


def first_hit_rank(source_document, passages):
    """1-based position of the first passage from the expected document."""
    for rank, passage in enumerate(passages, start=1):
        if passage.source == source_document:
            return rank
    return None


def evaluate_configuration(collection_name, eval_set):
    retriever = Retriever(collection_name=collection_name)
    answerable = [item for item in eval_set if item["answerable"]]

    records = []
    for item in answerable:
        passages = retriever.search(item["question"], top_k=SEARCH_DEPTH)
        rank = first_hit_rank(item["source_document"], passages)

        records.append({
            "id": item["id"],
            "category": item["category"],
            "rank": rank,
            "top_score": passages[0].score if passages else None,
        })

    hits = [r for r in records if r["rank"] is not None]
    top4_hits = [r for r in hits if r["rank"] <= 4]

    return {
        "questions": len(answerable),
        "hit_rate_at_10": round(len(hits) / len(answerable), 3),
        "hit_rate_at_4": round(len(top4_hits) / len(answerable), 3),
        "mean_rank": round(sum(r["rank"] for r in hits) / len(hits), 2) if hits else None,
        "mean_top_score": round(sum(r["top_score"] for r in records) / len(records), 3),
    }, records


def main():
    with EVAL_SET.open(encoding="utf-8") as handle:
        eval_set = json.load(handle)

    summaries = {}
    for config in CONFIGURATIONS:
        print(f"evaluating {config}...", flush=True)
        summary, records = evaluate_configuration(config, eval_set)
        summaries[config] = summary

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / f"retrieval_{config}.json").write_text(
            json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"\n{'=' * 74}")
    print(f"{'metric':22}" + "".join(f"{c:>17}" for c in CONFIGURATIONS))
    print(f"{'=' * 74}")

    for metric in ["hit_rate_at_4", "hit_rate_at_10", "mean_rank", "mean_top_score"]:
        row = f"{metric:22}"
        for config in CONFIGURATIONS:
            row += f"{str(summaries[config][metric]):>17}"
        print(row)

    print("\nhit_rate_at_4  — share of questions whose source document appears")
    print("                 in the top 4, the window the generator actually sees")
    print("mean_rank      — average position of the first correct passage;")
    print("                 lower is better")


if __name__ == "__main__":
    main()