

import argparse
import json
from pathlib import Path

from core.generation.rag_chain import DEFAULT_TOP_K
from core.retrieval.retriever import build_retriever

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"


def confidence_scores(mode, top_k):
    """(id, answerable, confidence) for every question, where confidence is
    what RagChain's gate would see."""
    retriever = build_retriever(mode=mode.split("+")[0], rerank=mode.endswith("+rerank"))
    eval_set = json.loads(EVAL_SET.read_text(encoding="utf-8"))

    rows = []
    for item in eval_set:
        passages = retriever.search(item["question"], top_k=top_k)
        confidence = max((p.retrieval_score for p in passages), default=0.0)
        rows.append((item["id"], item["answerable"], round(confidence, 4)))
    return rows


def sweep(rows, step=0.01):
    answerable = [c for _id, a, c in rows if a]
    unanswerable = [c for _id, a, c in rows if not a]

    lo = min(c for _id, _a, c in rows)
    hi = max(c for _id, _a, c in rows)

    table = []
    t = round(lo, 2)
    while t <= hi + 1e-9:
        false_refusals = sum(1 for c in answerable if c < t)
        correct_refusals = sum(1 for c in unanswerable if c < t)
        false_answers = len(unanswerable) - correct_refusals
        table.append(
            {
                "threshold": round(t, 2),
                "false_refusals": false_refusals,
                "correct_refusals": correct_refusals,
                "false_answers": false_answers,
                "accuracy": round(
                    (len(answerable) - false_refusals + correct_refusals) / len(rows), 3
                ),
            }
        )
        t += step
    return table, answerable, unanswerable


def best_threshold(table):

    safe = [row for row in table if row["false_refusals"] == 0]
    if not safe:
        return None
    return max(safe, key=lambda row: (row["correct_refusals"], row["threshold"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modes", nargs="+", default=["dense", "hybrid"])
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()

    report = {}
    for mode in args.modes:
        print(f"\n=== {mode} (top_k={args.top_k}) ===", flush=True)
        rows = confidence_scores(mode, args.top_k)
        table, answerable, unanswerable = sweep(rows)

        print(f"answerable   confidence: {sorted(answerable)}")
        print(f"unanswerable confidence: {sorted(unanswerable)}")
        print(f"\n{'thresh':>7}{'false_ref':>11}{'ok_ref':>8}{'false_ans':>11}{'acc':>7}")
        for row in table:
            print(
                f"{row['threshold']:>7}{row['false_refusals']:>11}"
                f"{row['correct_refusals']:>8}{row['false_answers']:>11}{row['accuracy']:>7}"
            )

        pick = best_threshold(table)
        if pick:
            print(
                f"\nbest zero-false-refusal cutoff: {pick['threshold']} "
                f"→ catches {pick['correct_refusals']}/{len(unanswerable)} unanswerable, "
                f"{pick['false_answers']} still pass through"
            )
        else:
            print("\nno cutoff refuses zero answerable questions")

        report[mode] = {
            "rows": [{"id": i, "answerable": a, "confidence": c} for i, a, c in rows],
            "sweep": table,
            "recommended": pick,
        }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "threshold_calibration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten: {RESULTS_DIR / 'threshold_calibration.json'}")


if __name__ == "__main__":
    main()
