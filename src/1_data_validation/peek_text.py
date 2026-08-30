"""What does pypdf actually see in this file?"""

from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET = BASE_DIR / "data" / "calibration_data" / "قانون اعطاي مدرك كارشناسي و بالاتر به حافظان كل قرآن.pdf"

text = "\n".join(p.extract_text() or "" for p in PdfReader(TARGET).pages)
print(text[:800])