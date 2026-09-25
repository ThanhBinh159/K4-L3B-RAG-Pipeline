"""BM25 retrieval over exactly the chunks used by the dense index."""

from __future__ import annotations

import re


CORPUS: list[dict] = []
_INDEX = None
_INDEX_CORPUS_ID = None
_STOP_WORDS = {
    "theo", "danh", "sách", "năm", "dùng", "để", "làm", "gì", "những", "nào",
    "là", "có", "của", "trong", "về", "cho", "và", "một", "với", "tại", "được",
    "các", "cần", "phải", "khi", "từ", "đến", "này", "đó", "thì", "hay", "hoặc",
}


def _tokens(text: str) -> list[str]:
    normalized = text.casefold()
    normalized = re.sub(
        r"\bmẫu\s+số\s+0*(\d+)\b",
        lambda match: f"mẫu_số_{int(match.group(1))}", normalized,
    )
    normalized = re.sub(
        r"\bđiều\s+0*(\d+)\b",
        lambda match: f"điều_{int(match.group(1))}", normalized,
    )
    tokens = re.findall(r"[^\W_]+(?:_[^\W_]+)*", normalized, flags=re.UNICODE)
    return [token for token in tokens if token not in _STOP_WORDS and not token.isdigit()]


def build_bm25_index(corpus: list[dict]):
    from rank_bm25 import BM25Plus

    if not corpus:
        return None
    return BM25Plus([_tokens(item["content"]) for item in corpus])


def _corpus_and_index():
    global CORPUS, _INDEX, _INDEX_CORPUS_ID
    if not CORPUS:
        from .task4_chunking_indexing import chunk_documents, load_documents

        CORPUS = chunk_documents(load_documents())
    if _INDEX_CORPUS_ID != id(CORPUS):
        _INDEX = build_bm25_index(CORPUS)
        _INDEX_CORPUS_ID = id(CORPUS)
    return CORPUS, _INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    if not query.strip() or top_k <= 0:
        return []
    corpus, index = _corpus_and_index()
    if index is None:
        return []
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return []
    scores = index.get_scores(list(query_tokens))
    tokenized_content = [_tokens(item["content"]) for item in corpus]
    ranked = sorted(range(len(corpus)), key=lambda i: float(scores[i]), reverse=True)
    results = []
    for position in ranked:
        score = float(scores[position])
        if not query_tokens.intersection(tokenized_content[position]):
            continue
        if score <= 0 or len(results) >= top_k:
            break
        item = corpus[position]
        results.append({
            "id": item["id"], "content": item["content"], "score": score,
            "metadata": item["metadata"], "retrieval_method": "bm25",
        })
    return results


if __name__ == "__main__":
    for item in lexical_search("mã số thuế hộ kinh doanh", top_k=3):
        print(item["score"], item["metadata"].get("source"))
