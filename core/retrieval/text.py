
import hazm

_normalizer = hazm.Normalizer()
_stopwords = frozenset(hazm.stopwords_list())

_PUNCTUATION = frozenset(
    "،؛؟!٪…«»”“\"'`.,:;()[]{}/\\|-–—ـ*#=+<>~^ "
)


def normalize(text: str) -> str:
    return _normalizer.normalize(text)


def tokenize(text: str) -> list[str]:
    tokens = hazm.word_tokenize(normalize(text))
    return [
        token
        for token in tokens
        if token not in _stopwords
        and token.strip() != ""
        and not all(char in _PUNCTUATION for char in token)
    ]
