"""Hybrid retrieval with a PageIndex fallback on weak dense evidence."""

import logging
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or 0.3)
DEFAULT_TOP_K = 5
logger = logging.getLogger(__name__)
_TRACKING_PARAMS = {"from", "ref", "source", "fbclid", "gclid"}


def _source_key(item: dict) -> str:
    metadata = item["metadata"]
    url = metadata.get("url")
    if not url:
        return metadata.get("source") or item["id"]
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.casefold() not in _TRACKING_PARAMS and not key.casefold().startswith("utm_")]
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"),
                       urlencode(query), ""))


def _merge_source_chunks(results: list[dict]) -> list[dict]:
    """Return one citation record per source while preserving retrieved context."""
    grouped: dict[str, dict] = {}
    contents: dict[str, list[str]] = {}
    for item in results:
        key = _source_key(item)
        if key not in grouped:
            grouped[key] = {**item, "metadata": {**item["metadata"], "url": key if item["metadata"].get("url") else None}}
            contents[key] = []
        content = item["content"].strip()
        if content and content not in contents[key]:
            contents[key].append(content)
        grouped[key]["score"] = max(float(grouped[key]["score"]), float(item["score"]))
    merged = []
    for key, item in grouped.items():
        item["content"] = "\n\n".join(contents[key])
        merged.append(item)
    return sorted(merged, key=lambda item: item["score"], reverse=True)


def _matches_query_anchors(query: str, content: str) -> bool:
    anchors = []
    anchors.extend(
        ("mẫu", number, bool(has_so))
        for has_so, number in re.findall(r"\bmẫu\s+(số\s+)?(\d+)\b", query, re.I)
    )
    anchors.extend(("điều", number, False)
                   for number in re.findall(r"\bđiều\s+(\d+)\b", query, re.I))
    if not anchors:
        return True
    normalized = " ".join(content.casefold().split())
    def anchor_pattern(kind: str, number: str, has_so: bool) -> str:
        middle = r"\s+số\s+" if kind == "mẫu" and has_so else r"\s+"
        return rf"\b{kind}{middle}{re.escape(number)}\b"

    return all(re.search(anchor_pattern(kind, number, has_so), normalized, re.I)
               for kind, number, has_so in anchors)


def _rank_sources(query: str, results: list[dict], top_k: int) -> list[dict]:
    merged = _merge_source_chunks(results)
    return [item for item in merged if _matches_query_anchors(query, item["content"])][:top_k]


def retrieve(query: str, top_k: int = DEFAULT_TOP_K, score_threshold: float = SCORE_THRESHOLD,
             use_reranking: bool = True) -> list[dict]:
    if not query.strip() or top_k <= 0:
        return []
    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2) if use_reranking else []
    hybrid = rerank_rrf([dense, sparse], top_k=top_k * 2) if use_reranking else dense
    best_dense_score = dense[0]["score"] if dense else 0.0
    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return _rank_sources(query, fallback, top_k)
        except Exception:
            logger.exception("PageIndex fallback failed")
    return _rank_sources(query, hybrid, top_k)


if __name__ == "__main__":
    for item in retrieve("Mã số thuế của hộ kinh doanh là gì?", top_k=3):
        print(item["score"], item["metadata"]["source"])
