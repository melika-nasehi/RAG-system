# Cross-encoder reranking

## What was added

| File | Purpose |
|------|---------|
| [`core/retrieval/rerank.py`](../core/retrieval/rerank.py) | `CrossEncoderReranker` (scores a query+passage pair jointly, reorders by relevance) and `RerankingRetriever` (wrapper: pull a wide pool from a base retriever, rerank down to top-k). Same `search(question, top_k=…)` interface. |
| [`core/retrieval/retriever.py`](../core/retrieval/retriever.py) | `build_retriever(mode=…, rerank=None)`. `rerank` → `RERANK` env (`1/true/yes/on`). When on, the base retriever (dense or hybrid) is wrapped in the reranking stage. |
| [`core/generation/rag_chain.py`](../core/generation/rag_chain.py) | `RagChain(…, rerank=None)` threaded through to the factory. |
| [`core/evaluation/compare_retrieval.py`](../core/evaluation/compare_retrieval.py) | Modes now include `dense+rerank`, `hybrid+rerank`. |

Model: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (~120 MB, XLM-RoBERTa backbone, downloaded once and cached). Override with `RERANK_MODEL`. Loaded lazily — a deployment with `RERANK` off never imports `sentence-transformers`.

Tests: [`tests/test_rerank.py`](../tests/test_rerank.py) — 7 (reorder logic with a fake scorer, top-k, pool width, interface parity, + 1 real-model integration). Full unit suite: 34 passing.

### Why a cross-encoder and not Ollama

Ollama only exposes `generate` and `embed` — no reranking endpoint — so a cross-encoder has to come from `sentence-transformers`. An LLM-as-reranker (feed numbered passages to `generate()`, ask for an ordering) is possible and stays on the existing stack, but costs a full generation call per query; it is noted as an alternative, not implemented.

## Results — `evaluation_set.json`, retrieval depth 10, rerank pool 15

| Metric | dense | hybrid | dense+rerank | hybrid+rerank |
|---|---|---|---|---|
| hit_rate @ 4 | 1.000 | 1.000 | 1.000 | 1.000 |
| hit_rate @ 10 | 1.000 | 1.000 | 1.000 | 1.000 |
| mean first-hit rank | 1.083 | 1.083 | **1.083** | **1.167** ⚠️ |
| mean top score — answerable | 0.694 | 0.032 | 0.732 | 0.732 |
| mean top score — unanswerable | 0.554 | 0.031 | **0.092** | 0.138 |

(dense/hybrid "top score" is cosine / RRF; the reranked columns are the cross-encoder relevance, sigmoid of the logit, in (0,1).)

### Findings

**1. Reranking does not improve hit rate — no headroom.** Dense retrieval already scores a perfect hit rate on the 12 answerable questions, so there is nothing for the reranker to recover. Same conclusion as hybrid.

**2. Reranking *regresses* ranking on top of hybrid.** `hybrid+rerank` moved Q11 (`مهلت ارائه گواهی پزشکی…`) from rank 1 to rank 3, pushing mean rank 1.083 → 1.167. On top of dense it is rank-neutral (swaps Q10 2→1 and Q11 1→2, net zero). The correct passage stays within the top-4 window in every case, so the generator is unaffected — but the reranker is actively unhelpful for ordering on this corpus.

**3. The cross-encoder score separates answerable from unanswerable much better *in aggregate*** (means 0.73 vs 0.09, vs cosine's 0.69 vs 0.55) — for genuinely irrelevant retrievals the model returns near-zero relevance. This is the one clearly positive result and it matters for Part 3.

**4. …but the separation is still not clean, and this model underrates informal Persian.** Per-question cross-encoder top scores:

- answerable: `0.066, 0.147, 0.208, 0.656, 0.797, 0.930, …` — the three low outliers are **Q12, Q07, Q13**
- unanswerable: `0.018, 0.021, 0.121, 0.207`

Q12 (`اگه سر امتحان مریض بشم چیکار کنم؟`) and Q13 (`می‌تونم از ChatGPT…`) are *colloquial* phrasings; the correct document is retrieved (rank 1) but the cross-encoder — fine-tuned on formal MS-MARCO queries, with no Persian in its fine-tuning data — scores the match as low as a wrong retrieval. So a refusal threshold on the cross-encoder score would false-refuse the informal questions.

## Q16 revisited

`dense+rerank` gives Q16 a cross-encoder top score of **0.021** (vs cosine 0.433) — the reranker is very confident nothing retrieved is relevant, which is correct (Q16 is unanswerable). `hybrid+rerank` gives 0.131, still low. Reranking sharpens the "nothing here" signal without inventing an answer.

## Recommendation

**Leave reranking off by default on the current corpus.** It adds a 120 MB model and **~490 ms/query** (65 ms → 553 ms on CPU) for **zero hit-rate gain** and a ranking regression when combined with hybrid. It stays built and switchable (`RERANK=1`) because its value appears once dense retrieval is no longer at ceiling — a larger, noisier corpus, or more adversarial phrasing.

The genuinely useful takeaway is for **Part 3**: the cross-encoder relevance score is a better refusal signal than cosine *in aggregate*, but this lightweight model's weakness on informal Persian means it cannot be the sole signal. A stronger multilingual reranker (`jinaai/jina-reranker-v2-base-multilingual`, `Alibaba-NLP/gte-multilingual-reranker-base`) may close that gap — untested here to stay within the "lightweight" constraint; noted as a follow-up.

## Score-semantics debt (carried from Part 1, still open)

`Passage.score` now means three different things depending on pipeline: cosine (dense), RRF (hybrid), sigmoid(logit) (rerank). Part 3 needs one stable, interpretable signal. The plan for Part 3: thread the **dense cosine** through every stage as a separate field on `Passage`, so the confidence check has a consistent input regardless of which retrieval stages are active — and optionally also expose the cross-encoder score when reranking is on, since it is the better aggregate separator.
