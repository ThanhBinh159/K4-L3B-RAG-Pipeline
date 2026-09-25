"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_API_URL = os.getenv("PAGEINDEX_API_URL", "").rstrip("/")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_PATH = STANDARDIZED_DIR.parent.parent / ".pageindex_cache.json"


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY or not PAGEINDEX_API_URL:
        return
    cache = _read_cache()
    headers = {"Authorization": f"Bearer {PAGEINDEX_API_KEY}"}
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []:
        source = path.relative_to(STANDARDIZED_DIR).as_posix()
        if source in cache:
            continue
        with path.open("rb") as document:
            response = requests.post(
                f"{PAGEINDEX_API_URL}/documents",
                headers=headers,
                files={"file": (path.name, document, "text/markdown")},
                timeout=60,
            )
        response.raise_for_status()
        payload = response.json()
        document_id = payload.get("document_id") or payload.get("id") or payload.get("data", {}).get("id")
        if document_id:
            cache[source] = str(document_id)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not query.strip() or not PAGEINDEX_API_KEY or not PAGEINDEX_API_URL:
        return []
    cache = _read_cache()
    if not cache:
        upload_documents()
        cache = _read_cache()
    response = requests.post(
        f"{PAGEINDEX_API_URL}/search",
        headers={"Authorization": f"Bearer {PAGEINDEX_API_KEY}"},
        json={"query": query, "document_ids": list(cache.values()), "top_k": top_k},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    raw_results = payload.get("results") or payload.get("data", {}).get("results") or []
    source_by_id = {value: key for key, value in cache.items()}
    results = []
    for rank, item in enumerate(raw_results[:top_k], 1):
        source = source_by_id.get(str(item.get("document_id", "")), item.get("source", "pageindex"))
        path = STANDARDIZED_DIR / source
        results.append({
            "id": str(item.get("id") or f"pageindex-{rank}"),
            "content": str(item.get("content") or item.get("text") or "").strip(),
            "score": float(item.get("score", 1 / rank)),
            "metadata": {
                "source": source,
                "title": path.stem,
                "doc_type": "legal" if "legal" in path.parts else "news",
                "url": None,
                "chunk_index": int(item.get("chunk_index", rank - 1)),
            },
            "retrieval_method": "pageindex",
        })
    return [item for item in results if item["content"]]


def _read_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    try:
        value = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    upload_documents()
