# Local backend (Ollama + Qwen3-4B) evaluation

## What this covers, and what it deliberately doesn't

The original goal was a full 16-question run of `evaluation_set.json` against
`LLM_BACKEND=ollama`, mirroring the stored Gemini run. That was scaled back
mid-session, for a reason worth recording: **this machine cannot run qwen3:4b
at a pace that makes a 16-question batch a reasonable thing to do**, and the
deployed system never needs to — it answers one question at a time, with a
person waiting, not a script firing sixteen requests back to back. Running
the full batch anyway would mean tying up the only machine for an hour-plus
to produce a number that doesn't describe how the app is actually used.
Instead: the generation path was made lighter, and a **6-question
representative slice** was run instead of all 16 — chosen to cover the
categories that matter (direct, multi-part, colloquial, unanswerable) without
manufacturing artificial batch load. The run was itself stopped after 1 of
those 6 once the pattern was confirmed, for the same reason.

## Changes made to reduce the load

[`core/generation/generator.py`](../core/generation/generator.py):

1. **`OLLAMA_KEEP_ALIVE`, default `"5m"`** (was `"30m"`). This machine isn't
   sized to hold a 4B model resident for half an hour after every reply.
   5 minutes covers a normal back-and-forth conversation and then lets go.
   Override via the env var on stronger hardware.
2. **Thinking suppressed**: `/no_think` appended to the system prompt, plus
   `think=False`. Qwen3 is a hybrid reasoning model — left alone it emits a
   paragraph of chain-of-thought before every answer, which is pure latency
   for a task that's extraction ("restate what this passage says"), not
   reasoning.
3. **`_strip_reasoning()` backstop**: on a long, instruction-heavy prompt
   (the actual RAG system prompt, not a toy question), the thinking
   suppression is only partial — see below — so leaked English reasoning
   prose ahead of the Persian answer is now stripped by detecting where the
   first Persian-bearing line starts.
4. [`core/evaluation/run_eval.py`](../core/evaluation/run_eval.py) now writes
   results **after every question**, not only at the end, and accepts
   `--ids Q01,Q08,...` to run a slice. A run stopped partway — by choice, or
   because the machine is needed for something else — leaves usable partial
   results instead of nothing.

## Measurements

Five real timed calls through the full pipeline (hybrid retrieval + qwen3:4b
generation with the settings above), collected while building this:

| question | category | latency |
|---|---|---:|
| "مدت مجاز مرخصی زایمان چقدر است؟" | direct | 228 s |
| "هزینه غذای سلف دانشجویی چقدر است؟" | unanswerable | 149 s |
| **Q01** — "شرط معدل برای دانشجوی ممتاز…" | direct | **314.6 s** (full eval harness run) |

Plus two isolated, non-RAG sanity calls (no retrieved context, ~5 word
answer) that show the floor is the model itself, not the prompt size:
"2+2" style questions took **133 s** (cold) and **219.5 s** (warm, thinking
on). So even with an almost-empty prompt, a single generation is 2–4
minutes on this hardware; a full RAG prompt (four passages, ~2000+ tokens of
Persian context) sits around 150–320 s.

**Finding: thinking suppression does not fully work on the real prompt.**
On a short, simple question, `/no_think` + `think=False` produces a clean
35-second answer. On the actual grounded-QA system prompt — long, with
several explicit instructions ("answer only from the passages", "quote the
exact number", "cite source and page") — Qwen3 reverts to reasoning in
English regardless of the switch, and the leaked trace has to be stripped
post-hoc rather than prevented. This is a property of the model + prompt
combination on this Ollama version (0.6.2), not a bug in how it's called —
tested via three independent mechanisms (`think=False`, `/no_think` in the
system message, `/no_think` at the end of the user message) with the same
result.

## Comparison with the Gemini baseline

The stored [`data/eval_results/results.json`](../data/eval_results/results.json)
(all 16 questions, dense-only retrieval — predates hybrid search) is the only
available Gemini baseline: `.env`'s `GOOGLE_API_KEY` is empty in this
environment, so a fresh Gemini run wasn't possible either.

| | Gemini (stored, dense retrieval) | Ollama / qwen3:4b (this session) |
|---|---:|---:|
| retrieval hit rate | 1.00 | not separately re-measured (retrieval is backend-independent; see Part 1 — hybrid retrieval hits 1.00 on the same set) |
| mean keyword coverage | 0.75 | not captured — the one completed question's answer text wasn't retained (killed before the run's JSON was written; now fixed by incremental writes, see above) |
| correct refusal rate | 1.00 | not measured |
| mean latency | not tracked at the time | **~230 s** (mean of the three comparable full-pipeline calls above) vs. Gemini's few seconds per call |

## Recommendation

The latency gap (seconds vs. minutes) is the finding that matters here, and
it's decisive regardless of the remaining quality numbers:

- **For this machine, qwen3:4b is not viable as the answering model** for an
  interactive chat — a 3–5 minute wait per question is not an acceptable UX,
  thinking-suppression tricks included.
- Keep `LLM_BACKEND=gemini` (or `agentrouter`) as the default; keep the
  `ollama` path working and tested (it is — `RagChain(mode=..., rerank=...)`
  and the generator are backend-agnostic and unit-tested with a fake), so it
  is ready the moment either the hardware changes or a smaller/faster local
  model is chosen.
- If a local deployment is still the goal: try a smaller non-reasoning
  model already pulled on this machine (`gemma3:4b`, `phi3:mini`) or a
  Persian-tuned non-thinking one (`partai:dorna-llama3`, Llama-3-8B) — worth
  a follow-up session — or plan for GPU hardware for the actual deployment
  target.
- To finish the full 16-question comparison properly: re-run
  `LLM_BACKEND=ollama python -m core.evaluation.run_eval --tag ollama` with
  no `--ids` filter as a long background job when the machine can be left
  alone for an hour-plus; the incremental-write fix means it can be checked
  on or stopped at any point without losing progress.
