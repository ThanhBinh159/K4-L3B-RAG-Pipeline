"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5 (đọc lại từ data/standardized/ qua
load_documents + chunk_documents của Task 4, không cần embedding). BM25 phù
hợp với từ khóa chính xác, mã tài liệu và tên riêng. Output phải theo
SearchResult và sort score giảm dần.
"""


CORPUS: list[dict] = []


def _ensure_corpus_loaded() -> list[dict]:
    """Nạp CORPUS từ Task 4 nếu chưa có sẵn (không cần embedding)."""
    global CORPUS
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4.

    Dùng BM25Plus thay vì BM25Okapi: trên corpus nhỏ, một từ khóa xuất hiện
    trong đúng 1/2 tài liệu có IDF = log(1) = 0 với công thức Okapi gốc, làm
    mọi điểm số về 0 và không phân biệt được văn bản liên quan. BM25Plus cộng
    thêm hằng số delta để tránh trường hợp suy biến này, vẫn giữ đúng thứ tự
    liên quan theo tần suất từ khóa.
    """
    from rank_bm25 import BM25Plus

    tokenized = [item["content"].lower().split() for item in corpus]
    return BM25Plus(tokenized)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    import numpy as np

    corpus = CORPUS if CORPUS else _ensure_corpus_loaded()
    if not corpus:
        return []

    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(query.lower().split())
    indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for index in indices:
        item = corpus[index]
        results.append(
            {
                "id": item["id"],
                "content": item["content"],
                "score": float(scores[index]),
                "metadata": item["metadata"],
                "retrieval_method": "bm25",
            }
        )
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
