

import pytest

from core.generation.generator import _strip_reasoning, generate


def test_returns_plain_text_unchanged():
    assert _strip_reasoning("حداقل ۱۸ واحد") == "حداقل ۱۸ واحد"


def test_strips_everything_through_a_bare_closing_tag():

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

    text = generate(
        "Answer in one short Persian sentence.",
        "دو بعلاوه دو چند می‌شود؟",
        backend="ollama",
    )
    assert text.strip()
    assert any(marker in text for marker in ("۴", "4", "چهار"))
