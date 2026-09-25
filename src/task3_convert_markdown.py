"""Convert source snapshots to Markdown without overwriting curated law excerpts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = ROOT / "data" / "landing"
OUTPUT_DIR = ROOT / "data" / "standardized"


def convert_legal_docs() -> None:
    """Keep complete source PDF conversions as audit copies outside the RAG set."""
    source_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal_original"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_dir.glob("*")):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        output = output_dir / f"{path.stem}.md"
        if output.exists() and output.stat().st_mtime >= path.stat().st_mtime:
            continue
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            content = "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages).strip()
        else:
            from markitdown import MarkItDown

            content = (MarkItDown().convert(str(path)).text_content or "").strip()
        if not content:
            raise ValueError(f"Empty conversion: {path}")
        output.write_text(f"# {path.stem.replace('_', ' ')}\n\n{content}\n", encoding="utf-8")


def convert_news_articles() -> None:
    """Write stable Markdown snapshots from the source JSON files."""
    source_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_dir.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        required = ("url", "title", "date_crawled", "content_markdown")
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in required):
            raise ValueError(f"Invalid article metadata: {path}")
        markdown = (
            f"# {item['title']}\n\n"
            f"**Source:** {item['url']}\n\n"
            f"**Crawled:** {item['date_crawled']}\n\n"
            f"---\n\n{item['content_markdown'].strip()}\n"
        )
        output = output_dir / f"{path.stem}.md"
        if not output.exists() or output.read_text(encoding="utf-8") != markdown:
            output.write_text(markdown, encoding="utf-8")


def convert_all() -> None:
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
