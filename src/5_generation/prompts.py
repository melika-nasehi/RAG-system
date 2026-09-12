

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


USER_TEMPLATE = """متن‌های بازیابی‌شده:

{context}

---

پرسش: {question}"""


def format_context(passages):

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