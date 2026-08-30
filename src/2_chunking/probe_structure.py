"""How consistently do these documents use formal numbering?

Chunking strategy depends on this. If most documents mark "ماده" (article)
and "تبصره" (note) numbers, structure-aware splitting is worth building. If
that pattern is rare or inconsistent, a fixed-size splitter is the honest
choice — building structure-awareness for structure that isn't there just
adds complexity with no payoff.
"""

from pathlib import Path
import re

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"

# Persian legal documents number articles and notes with either Eastern
# Arabic digits (۱۲) or spelled-out ordinals (اول, دوم). Both appear in our
# corpus, so both are checked.
ARTICLE_PATTERN = re.compile(r'ماده[\s\u200c]*[-–]?[\s\u200c]*[۰-۹0-9]+')
NOTE_PATTERN = re.compile(r'تبصره[\s\u200c]*[۰-۹0-9]*')
CHAPTER_PATTERN = re.compile(r'فصل[\s\u200c]*[۰-۹0-9]*')


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def structure_profile(text):
    return {
        "chars": len(text),
        "articles": len(ARTICLE_PATTERN.findall(text)),
        "notes": len(NOTE_PATTERN.findall(text)),
        "chapters": len(CHAPTER_PATTERN.findall(text)),
    }


def main():
    pdfs = sorted(DATA_RAW_DIR.glob("*.pdf"))

    for pdf in pdfs:
        text = extract_text(pdf)
        profile = structure_profile(text)

        density = profile["articles"] / (profile["chars"] / 1000) if profile["chars"] else 0

        print(f"\n{pdf.name}")
        print(f"  chars     {profile['chars']:,}")
        print(f"  articles  {profile['articles']}")
        print(f"  notes     {profile['notes']}")
        print(f"  chapters  {profile['chapters']}")
        print(f"  density   {density:.2f} articles/1000 chars")


if __name__ == "__main__":
    main()