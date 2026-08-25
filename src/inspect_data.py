from pathlib import Path
import re
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

def extract_text_from_pdf(pdf_path):

    reader = PdfReader(pdf_path)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return pages