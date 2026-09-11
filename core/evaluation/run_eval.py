"""Run the evaluation set through the full RAG chain and score each answer.

Module form of src/evaluation/run_eval.py, with two additions the backend
comparison needs: per-question latency, and the backend/retriever config
recorded in the output.

Four things are measured, because they fail independently:

* retrieval hit   — was the source document retrieved at all?
* keyword coverage — do the numbers and key phrases of the reference answer
  appear in the generated one? A pre-score for human review, not a verdict.
* refusal          — for unanswerable questions, did the system decline?
* latency          — wall-clock seconds for the whole ask().

Run:  LLM_BACKEND=ollama python -m core.evaluation.run_eval --tag ollama
"""

import argparse
import json
import re
import time
from pathlib import Path

from core.generation.generator import active_backend
from core.generation.rag_chain import RagChain
from core.retrieval.retriever import DEFAULT_MODE

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"

# Phrases the model uses to decline — checked against generated text to score
# refusal behaviour on unanswerable questions.
REFUSAL_MARKERS = [
    "اطلاعاتی", "وجود ندارد", "یافت نشد", "نمی‌دانم", "نمیدانم",
    "ذکر نشده", "موجود نیست", "پاسخی", "مشخص نشده",
    "حاوی", "نیستند", "نمی‌باشند", "نمی‌باشد", "یافت نشد",
]

_NUMBER = re.compile(r"[۰-۹0-9]+")
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
MIN_KEYWORD_LENGTH = 5


def strip_thinking(text: str) -> str:
    """Qwen3 emits <think>…</think> before the answer when Ollama does not
    split it off. It must not count toward coverage or refusal detection."""
    return _THINK.sub("", text).strip()


def extract_keywords(reference: str) -> set:
    numbers = set(_NUMBER.findall(reference))
    words = {w for w in re.findall(r"[؀-ۿ]+", reference) if len(w) >= MIN_KEYWORD_LENGTH}
    return numbers | words


def keyword_coverage(reference: str, generated: str):
    keywords = extract_keywords(reference)
    if not keywords:
        return None
    found = sum(1 for k in keywords if k in generated)
    return round(found / len(keywords), 2)


def retrieval_hit(source_document, passages):
    if source_document is None:
        return None
    return any(p.source == source_document for p in passages)


def refused(text: str) -> bool:
    return any(marker in text for marker in REFUSAL_MARKERS)


def evaluate_item(chain, item):
    start = time.monotonic()
    answer = chain.ask(item["question"])
    latency = round(time.monotonic() - start, 1)

    text = strip_thinking(answer.text)

    result = {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "reference_answer": item["reference_answer"],
        "generated_answer": text,
        "sources_retrieved": [p.citation() for p in answer.passages],
        "top_retrieval_score": (
            max((p.retrieval_score for p in answer.passages), default=None)
        ),
        "latency_s": latency,
        "chain_refused": answer.refused,
    }

    if item["answerable"]:
        result["retrieval_hit"] = retrieval_hit(item["source_document"], answer.passages)
        result["keyword_coverage"] = keyword_coverage(item["reference_answer"], text)
        result["correctly_refused"] = None
    else:
        result["retrieval_hit"] = None
        result["keyword_coverage"] = None
        result["correctly_refused"] = answer.refused or refused(text)

    return result


def summarise(results):
    answerable = [r for r in results if r["retrieval_hit"] is not None]
    unanswerable = [r for r in results if r["correctly_refused"] is not None]

    hits = [r["retrieval_hit"] for r in answerable]
    coverages = [r["keyword_coverage"] for r in answerable if r["keyword_coverage"] is not None]
    refusals = [r["correctly_refused"] for r in unanswerable]
    # False refusal: an answerable question the model declined to answer.
    false_refusals = sum(1 for r in answerable if refused(r["generated_answer"]))
    latencies = [r["latency_s"] for r in results]

    return {
        "total_questions": len(results),
        "answerable_questions": len(answerable),
        "retrieval_hit_rate": round(sum(hits) / len(hits), 2) if hits else None,
        "mean_keyword_coverage": round(sum(coverages) / len(coverages), 2) if coverages else None,
        "false_refusals_on_answerable": false_refusals,
        "unanswerable_questions": len(unanswerable),
        "correct_refusal_rate": round(sum(refusals) / len(refusals), 2) if refusals else None,
        "mean_latency_s": round(sum(latencies) / len(latencies), 1),
        "max_latency_s": max(latencies),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=None, help="output file suffix, e.g. 'ollama'")
    parser.add_argument("--mode", default=DEFAULT_MODE, help="retriever mode")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument(
        "--ids",
        default=None,
        help="comma-separated question ids to run instead of the full set "
        "(e.g. Q01,Q05,Q13,Q16) — the app only ever answers one question at "
        "a time, so a full 16-question sweep is not what needs proving on "
        "slow local hardware; a representative slice is",
    )
    args = parser.parse_args()

    eval_set = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    if args.ids:
        wanted = set(args.ids.split(","))
        eval_set = [item for item in eval_set if item["id"] in wanted]

    chain = RagChain(mode=args.mode, rerank=args.rerank)
    backend = active_backend()

    print(f"backend={backend}  retriever={args.mode}{'+rerank' if args.rerank else ''}\n", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"eval_{args.tag}.json" if args.tag else "eval.json"
    out_path = RESULTS_DIR / name

    # Written after every question, not just at the end — a slow local model
    # means this can run for a long time, and a run stopped partway (Ctrl-C,
    # or the machine needed for something else) should still leave usable
    # partial results instead of nothing.
    results = []

    def flush_partial():
        summary = summarise(results)
        summary["backend"] = backend
        summary["retriever"] = args.mode + ("+rerank" if args.rerank else "")
        summary["complete"] = len(results) == len(eval_set)
        out_path.write_text(
            json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    try:
        for item in eval_set:
            print(f"  {item['id']}: {item['question'][:48]}…", flush=True)
            record = evaluate_item(chain, item)
            print(f"       {record['latency_s']}s", flush=True)
            results.append(record)
            summary = flush_partial()
    except KeyboardInterrupt:
        summary = flush_partial()
        print(f"\nstopped after {len(results)}/{len(eval_set)} — partial results written", flush=True)

    print(f"\n{'=' * 50}\nSUMMARY  ({backend})\n{'=' * 50}")
    for key, value in summary.items():
        print(f"  {key:32} {value}")
    print(f"\nwritten to {(RESULTS_DIR / name).relative_to(BASE_DIR)}")
    print("Review each answer — keyword coverage is a signal, not a verdict.")


if __name__ == "__main__":
    main()
