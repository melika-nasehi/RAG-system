

import argparse
import json
from pathlib import Path

from core.retrieval.retriever import build_retriever

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"

SEARCH_DEPTH = 10

MODES = ("dense", "hybrid", "dense+rerank", "hybrid+rerank")


def retriever_for(mode):
    base, _, suffix = mode.partition("+")
    return build_retriever(mode=base, rerank=(suffix == "rerank"))


def load_eval_set():
    with EVAL_SET.open(encoding="utf-8") as handle:
        return json.load(handle)


def first_hit_rank(source_document, passages):
    for rank, passage in enumerate(passages, start=1):
        if passage.source == source_document:
            return rank
    return None


def evaluate(retriever, eval_set, search_depth=SEARCH_DEPTH):
    records = []
    for item in eval_set:
        passages = retriever.search(item["question"], top_k=search_depth)
        top = passages[0] if passages else None

        record = {
            "id": item["id"],
            "category": item["category"],
            "answerable": item["answerable"],
            "top_score": round(top.score, 4) if top else None,
            "top_source": top.source if top else None,
        }
        if item["answerable"]:
            record["rank"] = first_hit_rank(item.get("source_document"), passages)
        records.append(record)

    return summarize(records), records


def summarize(records):
    answerable = [r for r in records if r["answerable"]]
    unanswerable = [r for r in records if not r["answerable"]]

    hits = [r for r in answerable if r["rank"] is not None]
    top4 = [r for r in hits if r["rank"] <= 4]

    def mean(values):
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 3) if values else None

    return {
        "answerable": len(answerable),
        "hit_rate_at_4": round(len(top4) / len(answerable), 3) if answerable else None,
        "hit_rate_at_10": round(len(hits) / len(answerable), 3) if answerable else None,
        "mean_first_hit_rank": mean([r["rank"] for r in hits]),
        "mean_top_score_answerable": mean([r["top_score"] for r in answerable]),
        "mean_top_score_unanswerable": mean([r["top_score"] for r in unanswerable]),
    }


def _fmt(value):
    return "—" if value is None else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modes", nargs="+", default=["dense", "hybrid"], choices=MODES)
    parser.add_argument("--depth", type=int, default=SEARCH_DEPTH)
    args = parser.parse_args()

    eval_set = load_eval_set()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summaries = {}
    all_records = {}
    for mode in args.modes:
        print(f"evaluating {mode}...", flush=True)
        retriever = retriever_for(mode)
        summary, records = evaluate(retriever, eval_set, args.depth)
        summaries[mode] = summary
        all_records[mode] = records
        (RESULTS_DIR / f"retrieval_{mode}.json").write_text(
            json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    metrics = [
        "hit_rate_at_4",
        "hit_rate_at_10",
        "mean_first_hit_rank",
        "mean_top_score_answerable",
        "mean_top_score_unanswerable",
    ]
    width = 26
    print("\n" + "=" * (width + 15 * len(args.modes)))
    print(f"{'metric':{width}}" + "".join(f"{m:>15}" for m in args.modes))
    print("=" * (width + 15 * len(args.modes)))
    for metric in metrics:
        row = f"{metric:{width}}"
        for mode in args.modes:
            row += f"{_fmt(summaries[mode][metric]):>15}"
        print(row)

    if len(args.modes) >= 2:
        left, right = args.modes[0], args.modes[1]
        print(f"\nper-question first-hit rank — {left} vs {right} (answerable only):")
        print(f"{'id':6}{left:>16}{right:>16}   note")
        lft = {r["id"]: r for r in all_records[left]}
        rgt = {r["id"]: r for r in all_records[right]}
        for qid in sorted(lft):
            if not lft[qid]["answerable"]:
                continue
            lr, rr = lft[qid]["rank"], rgt[qid]["rank"]
            note = ""
            if lr != rr:
                note = "improved" if (rr or 99) < (lr or 99) else "regressed"
            print(f"{qid:6}{_fmt(lr):>16}{_fmt(rr):>16}   {note}")


if __name__ == "__main__":
    main()
