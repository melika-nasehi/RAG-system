"""Run the evaluation set against every chunking configuration and compare.

Chunk size and overlap were adopted from external sources during the
chunking phase (documented in notes section 10.1) and never validated on
this corpus. This closes that gap: same 16 questions, same generation
backend, only the underlying chunk collection changes.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "5_generation"))
from rag_chain import RagChain

sys.path.insert(0, str(Path(__file__).parent))
from run_eval import evaluate_item, summarise

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"

CONFIGURATIONS = [
    "chunks_500_100",
    "chunks_750_200",
    "chunks_1000_200",
]


def run_configuration(collection_name, eval_set):
    print(f"\n{'=' * 50}")
    print(f"configuration: {collection_name}")
    print(f"{'=' * 50}")

    chain = RagChain(collection_name=collection_name)
    results = []
    for item in eval_set:
        print(f"  {item['id']}...", flush=True)
        results.append(evaluate_item(chain, item))

    return summarise(results), results


def main():
    with EVAL_SET.open(encoding="utf-8") as handle:
        eval_set = json.load(handle)

    all_summaries = {}
    for config in CONFIGURATIONS:
        summary, results = run_configuration(config, eval_set)
        all_summaries[config] = summary

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESULTS_DIR / f"results_{config}.json"
        output_path.write_text(
            json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        for key, value in summary.items():
            print(f"  {key:25} {value}")

    print(f"\n{'=' * 60}")
    print("COMPARISON")
    print(f"{'=' * 60}")
    metrics = ["retrieval_hit_rate", "mean_keyword_coverage", "correct_refusal_rate"]
    header = f"{'metric':25}" + "".join(f"{c:>18}" for c in CONFIGURATIONS)
    print(header)
    for metric in metrics:
        row = f"{metric:25}"
        for config in CONFIGURATIONS:
            value = all_summaries[config].get(metric)
            row += f"{str(value):>18}"
        print(row)


if __name__ == "__main__":
    main()