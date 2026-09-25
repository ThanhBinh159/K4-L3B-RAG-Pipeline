"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = None
    for path in sorted(legal_dir.iterdir()) if legal_dir.is_dir() else []:
        try:
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                content = html_to_text(data.get("content_html", ""))
                header = _header(data.get("title", path.stem), data.get("url", ""), data.get("date_crawled", ""))
                text = header + content
            elif path.suffix.lower() in {".pdf", ".doc", ".docx"}:
                if converter is None:
                    try:
                        from markitdown import MarkItDown
                        converter = MarkItDown()
                    except ImportError:
                        converter = False
                if converter:
                    text = converter.convert(str(path)).text_content
                elif path.suffix.lower() == ".pdf":
                    from pypdf import PdfReader
                    text = "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
                else:
                    raise RuntimeError("install markitdown to convert DOC/DOCX")
            else:
                continue
            if text.strip():
                (output_dir / f"{path.stem}.md").write_text(text.strip() + "\n", encoding="utf-8")
        except Exception as error:
            print(f"Failed: {path} — {error}")


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(news_dir.glob("*.json")) if news_dir.is_dir() else []:
        data = json.loads(path.read_text(encoding="utf-8"))
        content = data.get("content_markdown", "").strip()
        if not content:
            continue
        text = _header(data.get("title", path.stem), data.get("url", ""), data.get("date_crawled", "")) + content
        (output_dir / f"{path.stem}.md").write_text(text.strip() + "\n", encoding="utf-8")


def _header(title: str, url: str, crawled: str) -> str:
    return f"# {title}\n\n**Source:** {url}\n\n**Crawled:** {crawled}\n\n---\n\n"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append(text)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return "\n\n".join(parser.parts)


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
