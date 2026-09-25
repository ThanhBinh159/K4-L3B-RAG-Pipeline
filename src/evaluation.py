"""Đánh giá retrieval + generation với 4 metric."""

import json
from pathlib import Path

from .task4_chunking_indexing import embed_texts
from .task9_retrieval_pipeline import retrieve
from .task10_generation import generate_with_citation


GOLDEN_PATH = Path(__file__).parent.parent / "group_project" / "evaluation" / "golden_dataset.json"


def load_golden() -> list[dict]:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return data["questions"]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb + 1e-9)


def _is_relevant(source: str, relevant_docs: list[str]) -> bool:
    """Khớp tên file dù có prefix hkd_ hay không."""
    src_base = source.replace("hkd_", "").replace(".md", "")
    for rel in relevant_docs:
        rel_base = rel.split("/")[-1].replace("hkd_", "").replace(".md", "")
        if src_base == rel_base or src_base in rel_base or rel_base in src_base:
            return True
    return False


def evaluate_full(
    use_pipeline: bool = True,
    use_reranking: bool = True,
    top_k: int = 5,
) -> dict:
    golden = load_golden()
    total = len(golden)

    hits = 0
    recall_sum = 0.0
    precision_sum = 0.0
    relevance_sum = 0.0
    faithfulness_sum = 0.0
    details = []

    for item in golden:
        query = item["question"]
        relevant_docs = item["relevant_docs"]
        expected_keywords = [k.lower() for k in item["expected_keywords"]]

        # ---- Retrieval ----
        if use_pipeline:
            results = retrieve(query, top_k=top_k, use_reranking=use_reranking)
        else:
            from .task5_semantic_search import semantic_search
            results = semantic_search(query, top_k=top_k)

        retrieved_sources = [r["metadata"].get("source", "") for r in results]

        # Context Recall: relevant_docs nào xuất hiện trong retrieved?
        found = sum(
            1 for rel in relevant_docs
            if any(_is_relevant(src, [rel]) for src in retrieved_sources)
        )
        recall = found / max(len(relevant_docs), 1)
        recall_sum += recall
        if found > 0:
            hits += 1

        # Context Precision: trong top-k, bao nhiêu là relevant?
        n_relevant_retrieved = sum(
            1 for src in retrieved_sources
            if _is_relevant(src, relevant_docs)
        )
        precision = n_relevant_retrieved / max(len(results), 1)
        precision_sum += precision

        # ---- Generation ----
        gen = generate_with_citation(query, top_k=top_k)
        answer = gen["answer"]
        sources = gen["sources"]

        # Answer Relevance: cosine(embed(query), embed(answer))
        if answer and answer.strip():
            q_vec, a_vec = embed_texts([query, answer])
            relevance_sum += _cosine(q_vec, a_vec)

        # Faithfulness: tỷ lệ token trong answer xuất hiện trong context
        context = " ".join(r["content"].lower() for r in sources)
        answer_tokens = [t for t in answer.lower().split() if len(t) > 2]
        if answer_tokens:
            matched = sum(1 for t in answer_tokens if t in context)
            faithfulness_sum += matched / len(answer_tokens)

        # Keyword hit (để debug)
        joined = " ".join(r["content"].lower() for r in results)
        keyword_hit = any(kw in joined for kw in expected_keywords)

        details.append({
            "id": item["id"],
            "hit": found > 0,
            "keyword_hit": keyword_hit,
            "recall": round(recall, 3),
            "precision": round(precision, 3),
            "retrieval_source": gen["retrieval_source"],
            "top_sources": retrieved_sources,
        })

    return {
        "mode": ("hybrid+RRF" if (use_pipeline and use_reranking)
                 else "dense-only"),
        "total": total,
        "hit_rate": round(hits / total, 3),
        "context_recall": round(recall_sum / total, 3),
        "context_precision": round(precision_sum / total, 3),
        "answer_relevance": round(relevance_sum / total, 3),
        "faithfulness": round(faithfulness_sum / total, 3),
        "details": details,
    }


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Đánh giá A/B: dense-only vs hybrid+RRF")
    print("=" * 60)

    # A: dense-only
    print("\n[A] Dense-only")
    report_a = evaluate_full(use_pipeline=False, top_k=5)
    for k, v in report_a.items():
        if k != "details":
            print(f"  {k}: {v}")

    # B: hybrid + RRF
    print("\n[B] Hybrid + RRF")
    report_b = evaluate_full(use_pipeline=True, use_reranking=True, top_k=5)
    for k, v in report_b.items():
        if k != "details":
            print(f"  {k}: {v}")

    # Lưu report
    out_path = GOLDEN_PATH.parent / "evaluation_results.json"
    out_path.write_text(
        json.dumps({"dense_only": report_a, "hybrid_rrf": report_b},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nĐã lưu: {out_path}")