"""Run the evaluation set against the full RAG chain and score the result.

Three things are measured separately, because they fail independently:

- retrieval hit: did the source document even get retrieved? If not, no
  amount of generation quality can produce a correct answer.
- keyword coverage: an automatic pre-score, not a verdict — it checks
  whether the numbers and key phrases from the reference answer appear in
  the generated one. Free-text answers can't be graded exactly by a script.
- refusal correctness: for unanswerable questions, did the system decline
  rather than construct an answer from loosely related passages?

Keyword coverage is a signal to guide human review, not a substitute for it.
A score is written next to each answer so reviewing 15 items means reading
them, not re-deriving the numbers.
"""

import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "5_generation"))
from rag_chain import RagChain

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET = BASE_DIR / "data" / "evaluation_set.json"
RESULTS_DIR = BASE_DIR / "data" / "eval_results"

# Phrases the model uses to decline — checked against generated text to
# score refusal behaviour on unanswerable questions.
REFUSAL_MARKERS = [
    "اطلاعاتی", "وجود ندارد", "یافت نشد", "نمی‌دانم", "نمیدانم",
    "ذکر نشده", "موجود نیست", "پاسخی", "مشخص نشده",
    "حاوی", "نیستند", "نمی‌باشند", "نمی‌باشد",
]

NUMBER = re.compile(r'[۰-۹0-9]+')
# Words long enough that matching them isn't coincidence — the same
# threshold used for the vocabulary check during data validation.
MIN_KEYWORD_LENGTH = 5


def extract_keywords(reference):
    """Numbers and long words from a reference answer — the concrete details
    an answer has to reproduce to be checking the same fact."""
    numbers = set(NUMBER.findall(reference))
    words = {w for w in re.findall(r'[\u0600-\u06FF]+', reference) if len(w) >= MIN_KEYWORD_LENGTH}
    return numbers | words


def keyword_coverage(reference, generated):
    keywords = extract_keywords(reference)
    if not keywords:
        return None
    found = sum(1 for k in keywords if k in generated)
    return round(found / len(keywords), 2)


def retrieval_hit(source_document, passages):
    if source_document is None:
        return None
    return any(p.source == source_document for p in passages)


def refused(generated_text):
    return any(marker in generated_text for marker in REFUSAL_MARKERS)


def evaluate_item(chain, item):
    answer = chain.ask(item["question"])

    result = {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "reference_answer": item["reference_answer"],
        "generated_answer": answer.text,
        "sources_retrieved": [p.citation() for p in answer.passages],
        "top_score": answer.passages[0].score if answer.passages else None,
    }

    if item["answerable"]:
        result["retrieval_hit"] = retrieval_hit(item["source_document"], answer.passages)
        result["keyword_coverage"] = keyword_coverage(item["reference_answer"], answer.text)
        result["correctly_refused"] = None
    else:
        result["retrieval_hit"] = None
        result["keyword_coverage"] = None
        result["correctly_refused"] = refused(answer.text)

    return result


def summarise(results):
    answerable = [r for r in results if r["retrieval_hit"] is not None]
    unanswerable = [r for r in results if r["correctly_refused"] is not None]

    hits = [r["retrieval_hit"] for r in answerable]
    coverages = [r["keyword_coverage"] for r in answerable if r["keyword_coverage"] is not None]
    refusals = [r["correctly_refused"] for r in unanswerable]

    return {
        "total_questions": len(results),
        "answerable_questions": len(answerable),
        "retrieval_hit_rate": round(sum(hits) / len(hits), 2) if hits else None,
        "mean_keyword_coverage": round(sum(coverages) / len(coverages), 2) if coverages else None,
        "unanswerable_questions": len(unanswerable),
        "correct_refusal_rate": round(sum(refusals) / len(refusals), 2) if refusals else None,
    }


def main():
    with EVAL_SET.open(encoding="utf-8") as handle:
        eval_set = json.load(handle)

    chain = RagChain()
    results = []

    for item in eval_set:
        print(f"  {item['id']}: {item['question'][:50]}...", flush=True)
        results.append(evaluate_item(chain, item))

    summary = summarise(results)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "results.json"
    output_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")
    for key, value in summary.items():
        print(f"  {key:25} {value}")

    print(f"\nfull results written to {output_path.relative_to(BASE_DIR)}")
    print("Review each answer manually — keyword coverage is a signal, not a verdict.")


if __name__ == "__main__":
    main()