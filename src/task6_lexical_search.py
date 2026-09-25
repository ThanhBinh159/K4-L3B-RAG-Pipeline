"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import math
import re


CORPUS: list[dict] = []


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class _BM25:
    def __init__(self, corpus: list[dict]) -> None:
        self.tokens = [_tokens(item["content"]) for item in corpus]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        document_frequency: dict[str, int] = {}
        for tokens in self.tokens:
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        self.idf = {
            token: math.log(1 + (len(self.tokens) - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = []
        for tokens, length in zip(self.tokens, self.lengths):
            counts = {token: tokens.count(token) for token in set(tokens)}
            score = 0.0
            for token in query_tokens:
                if token not in counts:
                    continue
                frequency = counts[token]
                denominator = frequency + 1.5 * (0.25 + 0.75 * length / max(self.average_length, 1))
                score += self.idf.get(token, 0.0) * frequency * 2.5 / denominator
            scores.append(score)
        return scores


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    return _BM25(corpus)


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if top_k <= 0 or not query.strip():
        return []
    corpus = CORPUS
    if not corpus:
        from .task4_chunking_indexing import chunk_documents, load_documents
        corpus = chunk_documents(load_documents())
    if not corpus:
        return []
    scores = build_bm25_index(corpus).get_scores(_tokens(query))
    indices = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    return [
        {
            "id": corpus[index]["id"],
            "content": corpus[index]["content"],
            "score": float(scores[index]),
            "metadata": corpus[index]["metadata"],
            "retrieval_method": "bm25",
        }
        for index in indices[:top_k]
        if scores[index] > 0
    ]


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
