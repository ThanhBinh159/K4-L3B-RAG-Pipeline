"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs (trong pageindex_doc_ids.json) để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash
(Task 9 bọc pageindex_search trong try/except, nhưng hàm này vẫn nên tự thất
bại gọn gàng thay vì để lỗi mơ hồ).
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
DOC_ID_CACHE = Path(__file__).parent.parent / "pageindex_doc_ids.json"

REQUEST_TIMEOUT = 30


def _load_doc_id_cache() -> dict[str, str]:
    if DOC_ID_CACHE.exists():
        return json.loads(DOC_ID_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_doc_id_cache(cache: dict[str, str]) -> None:
    DOC_ID_CACHE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def upload_documents() -> None:
    """Upload tài liệu chưa có trong cache và lưu mapping source -> document ID."""
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY chưa được cấu hình trong .env")

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    cache = _load_doc_id_cache()

    if not STANDARDIZED_DIR.is_dir():
        print(f"Không tìm thấy {STANDARDIZED_DIR}. Chạy Task 3 trước.")
        return

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        key = path.relative_to(STANDARDIZED_DIR).as_posix()
        if key in cache:
            continue
        try:
            # SDK của PageIndex hiện chỉ nhận PDF; convert Markdown -> PDF
            # tạm thời trước khi upload (đảm bảo giữ nội dung, không đoán
            # field response — kiểm tra lại tên field thật khi tích hợp).
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=11)
            for line in path.read_text(encoding="utf-8").splitlines():
                pdf.multi_cell(0, 6, line)
            tmp_pdf = path.with_suffix(".tmp.pdf")
            pdf.output(str(tmp_pdf))

            response = client.upload(str(tmp_pdf), timeout=REQUEST_TIMEOUT)
            tmp_pdf.unlink(missing_ok=True)

            document_id = response.get("doc_id") or response.get("id")
            if not document_id:
                print(f"Upload {key}: không tìm thấy document id trong response")
                continue
            cache[key] = document_id
            print(f"Uploaded: {key} -> {document_id}")
        except Exception as error:
            print(f"Failed to upload {key}: {error}")

    _save_doc_id_cache(cache)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY:
        return []

    from pageindex import PageIndexClient

    client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    cache = _load_doc_id_cache()
    if not cache:
        return []

    results: list[dict] = []
    for source, document_id in cache.items():
        try:
            response = client.retrieve(
                doc_id=document_id, query=query, timeout=REQUEST_TIMEOUT
            )
        except Exception as error:
            print(f"PageIndex retrieve failed for {source}: {error}")
            continue

        nodes = response.get("nodes") or response.get("results") or []
        for rank, node in enumerate(nodes, 1):
            content = node.get("text") or node.get("content") or ""
            if not content.strip():
                continue
            score = node.get("relevance_score")
            if score is None:
                # API không trả score -> gán score giảm dần theo rank.
                score = 1.0 / rank
            results.append(
                {
                    "id": f"pageindex::{source}::{node.get('node_id', rank)}",
                    "content": content,
                    "score": float(score),
                    "metadata": {
                        "source": source,
                        "title": Path(source).stem,
                        "doc_type": "legal" if "legal" in source else "news",
                        "url": None,
                        "chunk_index": rank - 1,
                    },
                    "retrieval_method": "pageindex",
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    upload_documents()
