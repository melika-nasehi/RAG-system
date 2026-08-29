"""Can the hazm word list separate clean Persian from garbled?"""

from hazm import Normalizer, WordTokenizer, words_list

normalizer = Normalizer()
tokenizer = WordTokenizer()

words = words_list()
print(f"vocabulary entries: {len(words):,}")
print(f"first 5 raw entries: {words[:5]}")

# Figure out the shape before assuming it's a flat list of strings.
vocab = {w[0] if isinstance(w, (tuple, list)) else w for w in words}
print(f"unique surface forms: {len(vocab):,}")
print(f"sample: {list(vocab)[:10]}")

SAMPLES = {
    "clean": "دانشگاه زنجان موظف است مقررات آموزشی را رعایت کند",
    "garbled": "حفظ تظوم بظد کرم مفظدهقر نظر مجقد کدراندسی عآو نر وی",
    "mixed": "وزارت فرهنگ و موزش عدلی موظف است هر سدله یک کوره",
}

for label, text in SAMPLES.items():
    tokens = [t for t in tokenizer.tokenize(normalizer.normalize(text)) if len(t) >= 4]
    known = [t for t in tokens if t in vocab]

    print(f"\n--- {label} ---")
    print(f"  tokens {len(tokens)}, known {len(known)} -> {len(known)/len(tokens)*100:.0f}%")
    print(f"  known:   {known}")
    print(f"  unknown: {[t for t in tokens if t not in vocab]}")