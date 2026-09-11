# Retrieval-confidence threshold

## Goal

When the best retrieved passage is weak, refuse the question in `RagChain`
directly — no LLM call — instead of asking the model to answer from passages
that don't contain the answer. Cheaper, and the refusal becomes
deterministic rather than depending on the model following the grounding
prompt.

## What was added

| File | Change |
|------|--------|
| [`core/retrieval/retriever.py`](../core/retrieval/retriever.py) | `Passage.retrieval_score` — always the **dense cosine**, carried unchanged through fusion and reranking (0.0 for a BM25-only hit). This is the one stable signal the gate can rely on whatever the pipeline. |
| [`core/retrieval/hybrid.py`](../core/retrieval/hybrid.py), [`rerank.py`](../core/retrieval/rerank.py) | Preserve `retrieval_score` when they rewrite `score`. |
| [`core/generation/rag_chain.py`](../core/generation/rag_chain.py) | `RagChain(…, min_score=None)` → env `MIN_RETRIEVAL_SCORE`. Confidence = `max(p.retrieval_score for p in passages)`; below `min_score` → return `Answer(refused=True, text=LOW_CONFIDENCE_MESSAGE, passages=…)` with **no `generate()` call**. `Answer` gained a `refused: bool` field. |
| [`core/evaluation/calibrate_threshold.py`](../core/evaluation/calibrate_threshold.py) | New — sweeps thresholds over the eval set, reports false-refusal / false-answer counts at each cutoff. |
| [`tests/test_confidence_threshold.py`](../tests/test_confidence_threshold.py) | New — 8 tests (both error types, boundary, env var, max-not-first aggregation, disabled-by-default). |

Full unit suite: **42 passing**.

## Calibration — `evaluation_set.json`, top_k = 4

Confidence score per question (dense cosine, max over the 4 passages sent to the generator), sorted:

```
0.433  Q16  unanswerable   «اگر سر کلاس نروم…»
0.460  Q14  unanswerable   «هزینه غذای سلف…»
────────────────────────────────────────────  ← any cutoff in 0.47–0.56: 0 false refusals
0.564  Q13  ANSWERABLE     «می‌تونم از ChatGPT…» (colloquial — lowest real question)
0.625  Q09  unanswerable   «خوابگاه دخترانه دانشگاه تهران» (lexically ≈ the dorm regulation)
0.654  Q10  ANSWERABLE
0.654  Q07  ANSWERABLE
 …
0.699  Q15  unanswerable   «انتقالی به دانشگاه دیگر» (lexically ≈ the academic regulation)
0.715  Q02  ANSWERABLE
 …
0.791  Q06  ANSWERABLE
```

Threshold sweep (dense):

| threshold | false refusals | unanswerable caught | false answers | accuracy |
|---:|---:|---:|---:|---:|
| 0.44 | 0 | 1 / 4 | 3 | 0.81 |
| **0.47 – 0.56** | **0** | **2 / 4** | **2** | **0.875** |
| 0.57 | 1 (Q13) | 2 / 4 | 2 | 0.81 |
| 0.63 | 1 (Q13) | 3 / 4 | 1 | 0.875 |
| 0.66 | 4 | 3 / 4 | 1 | 0.69 |
| 0.70 | 7 | 4 / 4 | 0 | 0.56 |

## Result — partial success, and why it can't be more

**The classes overlap. No threshold cleanly separates answerable from unanswerable.**

- **Cleanly caught (score < 0.47):** Q14 ("cafeteria food price") and Q16 ("what happens if I skip class") — genuinely off-topic, no document matches them well.
- **Cannot be caught without false refusals:** Q09 and Q15 are unanswerable questions *phrased exactly like in-domain ones* and lexically dominated by a single document (dorm regulation / academic regulation). Their top cosine (0.62, 0.70) sits **above** the lowest answerable question, Q13 (0.564, a colloquial ChatGPT question). Catching them means refusing real questions.

So the gate is a **cheap first filter, not a replacement** for the prompt-level grounded refusal. `SYSTEM_PROMPT` already tells the model to say so when the passages don't contain the answer; the threshold just removes the two most clearly out-of-scope cases before they cost a call.

### Hybrid narrows the gap slightly

Under hybrid retrieval, Q15's confidence drops from 0.70 to **0.57** — RRF pushes the high-cosine-but-irrelevant passage out of the top-4, so the max dense score the gate sees is lower. At threshold 0.58, hybrid catches 3/4 unanswerable for 1 false refusal (Q13); dense can't. Minor, but it's a second reason hybrid is a reasonable default.

## Recommendation

Ship the gate, **opt-in**, recommended value **`MIN_RETRIEVAL_SCORE=0.5`**:

- 0 false refusals on the eval set, with ~0.06 margin below the lowest real question
- catches Q14 + Q16 — ~13% of the unanswerable load, deterministically and for free
- `0.55` is the ceiling on this data; not recommended because the eval set is only 16 questions and Q13's 0.564 is a single data point — a future colloquial question could land at 0.52

Left **off by default** (`min_score=None`) until validated on a larger question set. Enable with the env var, or `RagChain(min_score=0.5)`.

## Rejected sub-hypotheses (for the record)

- *"A cosine threshold can separate answerable from unanswerable."* — No. Q09/Q15 (unanswerable) outscore Q13 (answerable). Best achievable on this set: 2/4 unanswerable caught at 0 false refusals.
- *"The cross-encoder score (from Part 2) is a better gate signal."* — Better in aggregate (means 0.73 vs 0.09) but **worse at the boundary**: the lightweight reranker scores the colloquial Q12 at 0.066, below unanswerable Q09 at 0.207. Not used as the gate signal; dense cosine is more stable across phrasings.
