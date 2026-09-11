"""Tests for the generator module: its own logic, and — as an integration
check — that switching LLM_BACKEND actually reaches a different, working
backend rather than only ever exercising the default.

`_strip_reasoning` in particular was wrong once already: an earlier version
assumed Qwen3's leaked reasoning was pure English and could be found by "the
first line containing Persian text", but the reasoning itself quotes Persian
terms from the question throughout, so that heuristic never fired on real
output.
"""

import pytest

from core.generation.generator import _strip_reasoning, generate


def test_returns_plain_text_unchanged():
    assert _strip_reasoning("حداقل ۱۸ واحد") == "حداقل ۱۸ واحد"


def test_strips_everything_through_a_bare_closing_tag():
    """Reproduces the real failure: Ollama emitted a closing </think> with
    no matching opening tag in message.content, and the reasoning before it
    quotes Persian words while narrating in English — so a heuristic based
    on "first Persian text" would keep the reasoning instead of dropping it."""
    leaked = (
        'Okay, let\'s tackle this. The user asks about "دانشجوی ممتاز" '
        "and I should check the passages.\n</think>\n\n"
        "حداقل ۱۸ (منبع: آیین‌نامه — صفحه ۴)"
    )
    assert _strip_reasoning(leaked) == "حداقل ۱۸ (منبع: آیین‌نامه — صفحه ۴)"


def test_strips_a_balanced_think_block_too():
    balanced = "<think>reasoning هرچه باشد here</think>\nپاسخ نهایی"
    assert _strip_reasoning(balanced) == "پاسخ نهایی"


def test_keeps_text_after_the_last_closing_tag_if_there_are_several():
    text = "</think>first\n</think>final answer"
    assert _strip_reasoning(text) == "final answer"


@pytest.mark.integration
def test_ollama_backend_answers_a_simple_question():
    """Smoke test for the Ollama path specifically. The existing full-chain
    integration test (tests/test_rag_chain.py) only ever exercises whatever
    LLM_BACKEND defaults to (gemini, in .env); this calls generate() with an
    explicit backend override so both paths are proven to work, not just
    configured. Slow — this is Qwen3 on CPU — hence @integration, same as
    the gemini test."""
    text = generate(
        "Answer in one short Persian sentence.",
        "دو بعلاوه دو چند می‌شود؟",
        backend="ollama",
    )
    assert text.strip()
    assert any(marker in text for marker in ("۴", "4", "چهار"))
