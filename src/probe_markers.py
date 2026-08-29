"""Which markers matched, and where did they come from?"""

from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
TARGET = BASE_DIR / "data" / "calibration_data" / "قانون اعطاي مدرك كارشناسي و بالاتر به حافظان كل قرآن.pdf"

ARABIC_TO_PERSIAN = str.maketrans({
    "\u0643": "\u06A9", "\u064A": "\u06CC",
    "\u0649": "\u06CC", "\u0629": "\u0647",
})

MARKERS = [
    "دانشگاه", "آموزش", "تحصیلی", "دانشجو", "مصوب", "تبصره",
    "مقررات", "همچنین", "بنابراین", "براساس", "درصورت",
    "میشود", "هستند", "خواهد", "موظف", "مربوط",
]

NON_PERSIAN_CHAR = re.compile(r'[^\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]')

for i, page in enumerate(PdfReader(TARGET).pages, 1):
    raw = page.extract_text() or ""
    folded = unicodedata.normalize("NFKC", raw).translate(ARABIC_TO_PERSIAN)
    compact = NON_PERSIAN_CHAR.sub("", folded)

    print(f"\n--- page {i} ({len(compact)} persian chars) ---")
    for marker in MARKERS:
        pos = compact.find(marker)
        if pos >= 0:
            around = compact[max(0, pos - 25):pos + len(marker) + 25]
            print(f"  {marker:12} at {pos:5}  ...{around}...")