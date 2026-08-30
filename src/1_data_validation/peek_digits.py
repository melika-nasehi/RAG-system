"""Show the actual context around each date-like number."""

from pathlib import Path
import re

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TARGET = BASE_DIR / "data" / "raw" / "education-7731-education1402-final.pdf"

PATTERN = re.compile(
    r'([۰-۹0-9]{1,4})\s*[/-]\s*([۰-۹0-9]{1,2})\s*[/-]\s*([۰-۹0-9]{1,4})'
    r'|(?<![۰-۹0-9])([۰-۹0-9]{4})(?![۰-۹0-9])'
)

text = "\n".join(p.extract_text() or "" for p in PdfReader(TARGET).pages)

for match in PATTERN.finditer(text):
    start = max(0, match.start() - 60)
    end = min(len(text), match.end() + 60)
    context = " ".join(text[start:end].split())
    print(f"\n[{match.group()}]")
    print(f"  ...{context}...")