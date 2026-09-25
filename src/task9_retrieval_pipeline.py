"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần (chỉ khi use_reranking=True).
    3. Lấy best cosine score gốc từ dense results (KHÔNG phải RRF score).
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi hoặc rỗng, trả hybrid/dense results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau (cosine
similarity nằm trong [0, 1], RRF score là tổng nghịch đảo rank).
"""

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)

    if use_reranking:
        hybrid = rerank_rrf([dense, sparse], top_k=top_k)
    else:
        hybrid = dense[:top_k]

    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
        except Exception as error:
            print(f"PageIndex fallback failed, keeping hybrid results: {error}")
            fallback = []
        if fallback:
            return fallback

    return hybrid[:top_k]


if __name__ == "__main__":
    for result in retrieve("test query", top_k=3):
        print(result)
