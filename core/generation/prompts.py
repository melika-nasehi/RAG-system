"""Prompt templates for grounded answering, kept separate from the code that
uses them.

A prompt is an experimental parameter, not a fixed part of the pipeline —
the same reasoning that put chunk size in a command-line flag. Having several
variants side by side is what makes comparing them possible later.

Instructions are in English because instruction-following data for these
models is overwhelmingly English, the same reason the embedding model's own
query prompt is English. The answer language is stated explicitly instead,
since the model would otherwise tend to reply in the language it was
instructed in.
"""

# The system instruction. Everything the model must and must not do lives
# here, not scattered through the user message.
SYSTEM_PROMPT = """You answer questions about Persian university regulations \
using only the passages provided to you.

Rules:
- Answer ONLY from the passages given. Never use outside knowledge, even if \
you are confident it is correct.
- If the passages do not contain the answer, say so plainly in Persian. Do \
not guess, and do not assemble an answer from loosely related passages.
- Quote the specific number, deadline or condition when the passages state \
one. These documents are regulations; precision matters more than fluency.
- Cite the source document and page for each fact you use.
- Write the answer in Persian, regardless of the language of these \
instructions."""


# Passages are numbered so the model has something concrete to cite, and the
# question comes last — models attend more reliably to the end of a long
# context.
USER_TEMPLATE = """متن‌های بازیابی‌شده:

{context}

---

پرسش: {question}"""


def format_context(passages):
    """Render retrieved passages with their provenance attached.

    Source and page travel with each passage rather than in a separate list,
    so the model can't mismatch a fact to the wrong citation.
    """
    blocks = []
    for index, passage in enumerate(passages, start=1):
        blocks.append(
            f"[{index}] منبع: {passage.source} — صفحه {passage.page}\n"
            f"{passage.text}"
        )
    return "\n\n".join(blocks)


def build_user_message(question, passages):
    return USER_TEMPLATE.format(
        context=format_context(passages),
        question=question,
    )