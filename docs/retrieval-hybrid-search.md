# Hybrid retrieval (dense + BM25)

## What was added

| File | Purpose |
|------|---------|
| [`core/retrieval/text.py`](../core/retrieval/text.py) | Persian normalisation + tokenisation (hazm). One function, shared by index and query so they tokenise identically. |
| [`core/retrieval/sparse.py`](../core/retrieval/sparse.py) | `SparseIndex` — Okapi BM25 over the chunk file. Pickled to `data/sparse_index/`, rebuilt automatically when the chunk file changes. |
| [`core/retrieval/hybrid.py`](../core/retrieval/hybrid.py) | `HybridRetriever` — pulls a candidate pool from dense and from BM25, fuses with Reciprocal Rank Fusion (k = 60), returns the same `list[Passage]` the dense retriever does. |
| [`core/retrieval/retriever.py`](../core/retrieval/retriever.py) | `build_retriever(mode=…)` factory. `mode` → `RETRIEVER_MODE` env → `DEFAULT_MODE = "hybrid"`. Hybrid import is deferred, so a dense-only deployment doesn't need hazm/rank-bm25. |
| [`core/generation/rag_chain.py`](../core/generation/rag_chain.py) | `RagChain(retriever=None, top_k=…, collection_name=None, mode=None)`. An explicit `retriever=` still wins (test doubles); otherwise the chain builds one through the factory. |
| [`core/evaluation/compare_retrieval.py`](../core/evaluation/compare_retrieval.py) | Scores any mode against `evaluation_set.json`; `python -m core.evaluation.compare_retrieval`. |

Tests: [`tests/test_sparse.py`](../tests/test_sparse.py) (8), [`tests/test_hybrid.py`](../tests/test_hybrid.py) (9, incl. exact RRF-maths checks with fakes). Full unit suite: 28 passing.

Dependencies (`rank-bm25`, `hazm`) were already installed in the venv; they are now declared in [`core/pyproject.toml`](../core/pyproject.toml). `requirements.txt` is UTF‑16 / not cleanly editable — left untouched.

## Fusion

Reciprocal Rank Fusion: a passage's score is `Σ 1/(k + rank)` over the lists it appears in, `k = 60`. Fusion is on **rank**, not score, so a cosine similarity and a BM25 score never have to be normalised onto the same scale. A passage that appears in both lists is scored once, from both contributions.

## Results — dense vs hybrid on `evaluation_set.json`

16 questions: 12 answerable, 4 unanswerable. Retrieval depth 10.

| Metric | Dense | Hybrid |
|---|---|---|
| hit_rate @ 4 (answerable) | **1.000** | **1.000** |
| hit_rate @ 10 (answerable) | **1.000** | **1.000** |
| mean first‑hit rank | **1.083** | **1.083** |
| mean top score — answerable | 0.694 (cosine) | 0.032 (RRF) |
| mean top score — unanswerable | 0.556 (cosine) | 0.031 (RRF) |

Per‑question first‑hit rank (answerable): **identical in every case** (Q10 at rank 2 in both, everything else rank 1).

### Reading of the result

**On this evaluation set, hybrid neither helps nor hurts.** Dense retrieval with Qwen3‑Embedding already scores a perfect hit rate on the 12 answerable questions, so there is no headroom for hybrid to recover. The important negative result is that **RRF did not push any correct passage out of the top‑4** — hybrid is a safe default.

Where hybrid *does* change the ranking (manual probes, not in the eval set): exact‑term queries like `«کمیته انضباطی بدوی و تجدید نظر»` — dense ranks the disciplinary‑council document #2, hybrid promotes it to #1. The value of the lexical channel will grow as the corpus and the range of phrasings grow; on today's 18‑document corpus it is marginal.

## Q16 — `«اگر سر کلاس نروم چه اتفاقی می‌افتد؟»`

This question is labelled **`answerable: false`** in `evaluation_set.json`. The corpus's academic regulation covers *exam* absence (ماده ۷ → grade zero) and class attendance for *makeup* courses, but has **no general "skip class" penalty article** (the usual «غیبت بیش از ۳/۱۶ جلسات» rule is not in any of the 18 documents). So the correct system behaviour is a low‑confidence refusal, not a retrieval.

| | Dense | Hybrid |
|---|---|---|
| Top‑1 source | آئین‌نامه یکپارچه، ص ۲۰ | آئین‌نامه یکپارچه، ص ۲۰ |
| Top score | **0.433** (cosine) | 0.032 (RRF) |
| Contains the answer? | No (there is none) | No |

**Hybrid does not "resolve" Q16, and it should not.** The earlier probe note (`src/5_generation/probe_lexical_gap.py`) framed the 0.42 score as a lexical gap / failure; the labelled eval set — added later — establishes that this is an *unanswerable* question and 0.42 is the system correctly signalling "nothing relevant". This is a **Part 3 (confidence threshold)** case, not a Part 1 retrieval failure. Hybrid's only job here was to not manufacture a confident wrong answer, and it doesn't.

## Consequence for Part 3 (confidence threshold)

**The RRF fused score is not a usable confidence signal** — it sits at ≈0.03 whether the question is answerable or not (see table above). The **dense cosine** score does separate the two populations:

- answerable top scores: `0.566 – 0.791`
- unanswerable top scores: `0.435, 0.464, 0.625, 0.700`

So a threshold on the dense cosine at ≈0.52 would refuse Q14 and Q16 correctly with zero false refusals, but still answer Q09 (0.625) and Q15 (0.700). The classes overlap; a cosine threshold alone cannot cleanly separate them. Part 3 will need to read the **dense** score even when hybrid is the active retriever — `Passage` currently reports the fused score for hybrid, so this needs a small plumbing change (carry the dense cosine alongside the fused score) handled in Part 3.
