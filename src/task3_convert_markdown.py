"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại (idempotent: chạy lại
       nhiều lần cho cùng input sẽ ghi đè đúng 1 file, không nhân bản).
"""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

SUPPORTED_LEGAL_EXTENSIONS = {".pdf", ".doc", ".docx"}


def convert_legal_docs() -> None:
    """Convert PDF/DOCX trong data/landing/legal/ vào data/standardized/legal/."""
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not legal_dir.is_dir():
        print(f"Không tìm thấy {legal_dir}, bỏ qua convert_legal_docs.")
        return

    converter = MarkItDown()
    converted = 0
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in SUPPORTED_LEGAL_EXTENSIONS:
            continue
        try:
            result = converter.convert(str(path))
        except Exception as error:
            print(f"Failed to convert {path.name}: {error}")
            continue

        text = (result.text_content or "").strip()
        if not text:
            print(f"Skip {path.name}: nội dung rỗng sau khi convert.")
            continue

        header = f"# {path.stem}\n\n**Source file:** {path.name}\n\n---\n\n"
        destination = output_dir / f"{path.stem}.md"
        destination.write_text(header + text, encoding="utf-8")
        print(f"Saved: {destination}")
        converted += 1

    print(f"Converted {converted} legal document(s).")


def convert_news_articles() -> None:
    """Convert JSON trong data/landing/news/ vào data/standardized/news/."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not news_dir.is_dir():
        print(f"Không tìm thấy {news_dir}, bỏ qua convert_news_articles.")
        return

    converted = 0
    for path in sorted(news_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"Failed to parse {path.name}: {error}")
            continue

        content = (data.get("content_markdown") or "").strip()
        if not content:
            print(f"Skip {path.name}: content_markdown rỗng.")
            continue

        header = (
            f"# {data.get('title', path.stem)}\n\n"
            f"**Source:** {data.get('url', '')}\n\n"
            f"**Crawled:** {data.get('date_crawled', '')}\n\n---\n\n"
        )
        destination = output_dir / f"{path.stem}.md"
        destination.write_text(header + content, encoding="utf-8")
        print(f"Saved: {destination}")
        converted += 1

    print(f"Converted {converted} news article(s).")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
