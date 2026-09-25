"""Task 2 — Kiểm tra các bài viết/news đã thu thập thủ công."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"
REQUIRED_FIELDS = {"url", "title", "date_crawled", "content_markdown"}


def validate_article(path: Path) -> dict:
    """Load and validate one manually collected article JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f"{path.name} missing: {', '.join(sorted(missing))}")
    if any(not str(data[field]).strip() for field in REQUIRED_FIELDS):
        raise ValueError(f"{path.name} contains empty required metadata")
    return data


def validate_articles(minimum: int = 5) -> int:
    """Validate local JSON files; never crawl or call an external URL."""
    files = sorted(DATA_DIR.glob("*.json")) if DATA_DIR.is_dir() else []
    if len(files) < minimum:
        raise RuntimeError(f"Expected at least {minimum} collected articles, found {len(files)}")
    for path in files:
        validate_article(path)
    return len(files)


def crawl_all() -> None:
    """Compatibility entry point: validate the already collected corpus."""
    print(f"Validated {validate_articles()} manually collected articles")


if __name__ == "__main__":
    crawl_all()
