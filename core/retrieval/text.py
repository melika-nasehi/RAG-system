"""Persian text preparation for lexical retrieval.

Both the BM25 index and the queries run against it must be tokenised the
exact same way, or a term in the question will not match the identical term
in a passage. Keeping that one function here — normalise, tokenise, drop
stopwords and punctuation — is what guarantees they stay in step.

Normalisation matters more in Persian than in English: the same word is
routinely written with Arabic or Persian yeh/kaf, with or without ZWNJ, and
with different spacing around affixes. hazm's Normalizer collapses those so
"كلاس" and "کلاس" land on the same token.
"""

import hazm

_normalizer = hazm.Normalizer()
_stopwords = frozenset(hazm.stopwords_list())

# Punctuation hazm's tokenizer emits as standalone tokens; none of it carries
# retrieval signal.
_PUNCTUATION = frozenset(
    "،؛؟!٪…«»”“\"'`.,:;()[]{}/\\|-–—ـ*#=+<>~^ "
)


def normalize(text: str) -> str:
    """Apply the same surface normalisation used when the index was built."""
    return _normalizer.normalize(text)


def tokenize(text: str) -> list[str]:
    """Content tokens of a query or passage, normalised and stopword-free."""
    tokens = hazm.word_tokenize(normalize(text))
    return [
        token
        for token in tokens
        if token not in _stopwords
        and token.strip() != ""
        and not all(char in _PUNCTUATION for char in token)
    ]
