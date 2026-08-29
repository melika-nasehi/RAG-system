"""Can dynamic-programming segmentation recover words that lost their spaces?

Fixed-width chopping fails because word boundaries don't fall on a grid.
This tries every possible split and keeps the one that produces the most
plausible sequence of real words.
"""

from functools import lru_cache
from math import log

from hazm import words_list

_frequency = {entry[0]: entry[1] for entry in words_list()}
_total = sum(_frequency.values())

# Persian words rarely run past this. Allowing more lets the segmenter
# swallow a whole run as one "word" and call it done.
MAX_WORD_LENGTH = 12

# Squared so that leaving a long run unsegmented is always worse than any
# sequence of real words. A linear penalty loses to a three-word split.
UNKNOWN_PENALTY = 25.0


def word_cost(word):
    """Negative log probability — rarer words cost more, unknown words most."""
    freq = _frequency.get(word, 0)
    if freq == 0:
        return UNKNOWN_PENALTY + len(word) ** 2
    return -log(freq / _total)


def segment(run):
    """Split a space-less run into the cheapest sequence of words."""

    @lru_cache(maxsize=None)
    def best(start):
        if start == len(run):
            return 0.0, ()

        best_cost = float("inf")
        best_path = ()

        for end in range(start + 1, min(start + MAX_WORD_LENGTH, len(run)) + 1):
            piece = run[start:end]
            rest_cost, rest_path = best(end)
            cost = word_cost(piece) + rest_cost

            if cost < best_cost:
                best_cost = cost
                best_path = (piece,) + rest_path

        return best_cost, best_path

    _, path = best(0)
    best.cache_clear()
    return list(path)


SAMPLES = [
    "انتشاراتدانشگاهزنجان",
    "نویسندهکتاب",
    "دراینبخشبهمواردزیراشارهمی",
    "نکاتمهمدرمطالعهودرکمطالبکتاب",
    "عنوانفصلاول",
    # Garbled text — should not segment into anything sensible.
    "کدراندسی",
    "مفظدهقر",
    "نظدوو",
]

for sample in SAMPLES:
    pieces = segment(sample)
    known = sum(1 for p in pieces if _frequency.get(p, 0) > 0)
    print(f"{sample}")
    print(f"  -> {pieces}")
    print(f"     {known}/{len(pieces)} real words\n")