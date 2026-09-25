"""Reciprocal rank fusion of the dense and BM25 result lists."""


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    if top_k <= 0 or k < 0:
        return []
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        seen = set()
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            if item_id in seen:
                continue
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            items.setdefault(item_id, item)
    ranked_ids = sorted(scores, key=lambda item_id: (-scores[item_id], item_id))
    return [
        {**items[item_id], "score": scores[item_id], "retrieval_method": "hybrid"}
        for item_id in ranked_ids[:top_k]
    ]


if __name__ == "__main__":
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    for item in rerank_rrf([semantic_search("mã số thuế hộ kinh doanh"), lexical_search("mã số thuế hộ kinh doanh")]):
        print(item["score"], item["metadata"]["source"])
