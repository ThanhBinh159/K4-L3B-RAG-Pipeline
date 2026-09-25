"""Task 1 — Thu thập văn bản pháp luật từ phapluat.gov.vn."""

import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
LIST_URL = "https://phapluat.gov.vn/api/legal-documents"
DETAIL_URL = "https://phapluat.gov.vn/api/legal-documents/detail"
HEADERS = {"Accept": "application/json", "User-Agent": "K4-L3B-RAG-Pipeline/1.0"}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def _safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return (re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._") or "legal_document")[:100]


def download_documents(limit: int = 3) -> int:
    """Lấy danh sách, tải detail và lưu JSON gốc; trả về số file đã lưu."""
    if limit < 1:
        raise ValueError("limit must be positive")
    session = requests.Session()
    session.headers.update(HEADERS)
    listing = session.post(LIST_URL, json={}, timeout=30)
    listing.raise_for_status()
    docs = listing.json().get("data", {}).get("docs", [])
    if len(docs) < limit:
        raise RuntimeError(f"API returned only {len(docs)} documents")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0
    for summary in docs[:limit]:
        doc_id = summary.get("docGUId")
        if not doc_id:
            continue
        detail = session.get(DETAIL_URL, params={"docGUId": doc_id, "tabName": "tomtat"}, timeout=30)
        detail.raise_for_status()
        document = detail.json().get("data") or {}
        if not document.get("docContent"):
            continue
        record = {
            "url": f"https://phapluat.gov.vn/van-ban/chi-tiet/{doc_id}",
            "title": document.get("docNameClear") or document.get("docName", ""),
            "date_crawled": datetime.now().isoformat(),
            "docGUId": doc_id,
            "docIdentity": document.get("docIdentity", ""),
            "issueDate": document.get("issueDate", ""),
            "effectDate": document.get("effectDate", ""),
            "content_html": document["docContent"],
        }
        stem = _safe_filename(record["docIdentity"] or record["title"])
        (DATA_DIR / f"{stem}_{doc_id[:8]}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    setup_directory()
    print(f"Saved {download_documents(args.limit)} legal documents")
