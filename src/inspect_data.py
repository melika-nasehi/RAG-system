"""Sanity-check source PDFs before they hit the pipeline."""

from pathlib import Path
import re

from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

# Clean Persian PDFs run above 70%. The broken 1376 circular came in at 11%.
MIN_CHARS_PER_PAGE = 100
MIN_PERSIAN_RATIO = 60.0
EMPTY_PAGE_THRESHOLD = 50

PERSIAN_BLOCK = re.compile(r'[\u0600-\u06FF]')
WHITESPACE = re.compile(r'\s')


def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def measure(pages):
    full_text = "\n".join(pages)
    stripped = WHITESPACE.sub("", full_text)

    persian_count = len(PERSIAN_BLOCK.findall(full_text))
    total_count = len(stripped)

    return {
        "pages": len(pages),
        "chars": total_count,
        "chars_per_page": total_count // len(pages) if pages else 0,
        "blank_pages": sum(1 for p in pages if len(p.strip()) < EMPTY_PAGE_THRESHOLD),
        "persian_ratio": round(persian_count / total_count * 100, 1) if total_count else 0.0,
    }


def verdict(stats):
    # Check scan first — ratio is meaningless with almost no characters.
    if stats["chars_per_page"] < MIN_CHARS_PER_PAGE:
        return False, "scanned; no extractable text"

    if stats["persian_ratio"] < MIN_PERSIAN_RATIO:
        return False, f"{stats['persian_ratio']}% Persian — likely broken font mapping"

    return True, "ok"


def main():
    pdfs = sorted(DATA_RAW_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs found in {DATA_RAW_DIR}")
        return

    for pdf in pdfs:
        stats = measure(extract_pages(pdf))
        ok, reason = verdict(stats)

        print(f"\n{pdf.name}")
        print(f"  pages          {stats['pages']}")
        print(f"  chars          {stats['chars']:,}")
        print(f"  chars/page     {stats['chars_per_page']:,}")
        print(f"  blank pages    {stats['blank_pages']}")
        print(f"  persian ratio  {stats['persian_ratio']}%")
        print(f"  -> {'ACCEPT' if ok else 'REJECT'}: {reason}")


if __name__ == "__main__":
    main()