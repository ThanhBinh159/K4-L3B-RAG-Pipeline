"""Cosine dense retrieval over the Task 4 Chroma collection."""

from .task4_chunking_indexing import _EMBED_INPUT_TYPE, embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    if not query.strip() or top_k <= 0:
        return []
    token = _EMBED_INPUT_TYPE.set("search_query")
    try:
        vector = embed_texts([query])
    finally:
        _EMBED_INPUT_TYPE.reset(token)
    response = get_collection().query(
        query_embeddings=vector,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    seen = set()
    for item_id, content, metadata, distance in zip(
        response["ids"][0], response["documents"][0],
        response["metadatas"][0], response["distances"][0],
    ):
        if item_id in seen:
            continue
        seen.add(item_id)
        results.append({
            "id": item_id,
            "content": content,
            "score": max(0.0, 1.0 - float(distance)),
            "metadata": {"url": None, **(metadata or {})},
            "retrieval_method": "dense",
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for item in semantic_search("Mã số thuế của hộ kinh doanh là gì?", top_k=3):
        print(item["score"], item["metadata"].get("source"))
