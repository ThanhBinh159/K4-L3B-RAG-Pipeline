"""Reproducible offline evaluation of dense and hybrid retrieval.

These are deterministic lexical proxies, not RAGAS or an LLM judge.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .task9_retrieval_pipeline import retrieve
from .task10_generation import REFUSAL, _extract_answer
from .task4_chunking_indexing import EMBEDDING_MODEL, EMBEDDING_PROVIDER


ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
REPORT_PATH = ROOT / "group_project" / "evaluation" / "RESULT.md"


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.casefold()))


def answer_relevance(answer: str, expected: str) -> float:
    """Token F1 against the reference answer, excluding citation markers."""
    if answer == REFUSAL:
        return 0.0
    actual = tokens(re.sub(r"\[\d+\]", "", answer))
    gold = tokens(expected)
    if not actual or not gold:
        return 0.0
    common = len(actual & gold)
    return 2 * common / (len(actual) + len(gold))


def faithfulness(answer: str, sources: list[dict]) -> float:
    """One if the quoted answer span occurs verbatim in its cited source."""
    if answer == REFUSAL:
        return 0.0
    match = re.search(r"“(.+?)”\s*\[(\d+)\]", answer, flags=re.DOTALL)
    if not match:
        return 0.0
    index = int(match.group(2)) - 1
    if index < 0 or index >= len(sources):
        return 0.0
    return float(match.group(1).rstrip("…") in sources[index]["content"])


def is_relevant(source: dict, case: dict) -> bool:
    metadata = source["metadata"]
    if metadata.get("url") != case.get("source_url"):
        return False
    return not case.get("article") or metadata.get("article") == case["article"]


def context_metrics(sources: list[dict], case: dict) -> tuple[float, float]:
    """Gold source/article hit and average precision at k over retrieved chunks."""
    relevant = [is_relevant(source, case) for source in sources]
    recall = float(any(relevant))
    hits = 0
    precision_sum = 0.0
    for rank, hit in enumerate(relevant, 1):
        if hit:
            hits += 1
            precision_sum += hits / rank
    return recall, precision_sum / hits if hits else 0.0


def evaluate_case(case: dict, *, hybrid: bool, top_k: int = 5) -> dict:
    sources = retrieve(case["question"], top_k=top_k, score_threshold=-1,
                       use_reranking=hybrid)
    answer, cited = _extract_answer(case["question"], sources)
    recall, precision = context_metrics(sources, case)
    return {
        "question": case["question"], "answer": answer,
        "source_ids": [source["id"] for source in sources],
        "faithfulness": faithfulness(answer, cited),
        "answer_relevance": answer_relevance(answer, case["expected_answer"]),
        "context_recall": recall, "context_precision": precision,
    }


def evaluate_all() -> dict:
    cases = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    results = {}
    for label, hybrid in (("dense", False), ("hybrid_rrf", True)):
        rows = [evaluate_case(case, hybrid=hybrid) for case in cases]
        metrics = {name: round(sum(row[name] for row in rows) / len(rows), 4)
                   for name in ("faithfulness", "answer_relevance", "context_recall", "context_precision")}
        results[label] = {"metrics": metrics, "rows": rows}
    return {"count": len(cases), "results": results}


def write_report(evaluation: dict) -> None:
    dense = evaluation["results"]["dense"]
    hybrid = evaluation["results"]["hybrid_rrf"]
    labels = ["faithfulness", "answer_relevance", "context_recall", "context_precision"]
    lines = [
        "# Evaluation: pháp luật hộ kinh doanh", "",
        f"Đánh giá trên {evaluation['count']} câu hỏi trong `golden_dataset.json`; "
        "cùng corpus, top_k=5 và cùng bộ trích xuất câu trả lời offline. "
        "Tắt PageIndex ở cả hai nhánh để so sánh retrieval.", "",
        "## Overall scores", "",
        "| Metric (offline proxy) | Dense only | Hybrid + RRF | Δ |", "| --- | ---: | ---: | ---: |",
    ]
    for name in labels:
        a, b = dense["metrics"][name], hybrid["metrics"][name]
        lines.append(f"| {name} | {a:.3f} | {b:.3f} | {b-a:+.3f} |")
    lines += [
        "", "## A/B comparison", "",
        "Dense dùng cosine trên Chroma; hybrid gộp thứ hạng dense và BM25Plus bằng RRF (k=60). "
        f"Cả hai dùng embedding `{EMBEDDING_PROVIDER}` (`{EMBEDDING_MODEL}`), cùng 15 câu, "
        "không gọi LLM và không gọi PageIndex.", "",
        "**Định nghĩa proxy:** faithfulness = đoạn trích trong câu trả lời xuất hiện nguyên văn ở source được dẫn; "
        "answer relevance = token F1 giữa câu trả lời và đáp án tham chiếu; "
        "context recall = có ít nhất một chunk đúng URL và đúng Điều (nếu có); "
        "context precision = average precision@5 trên các chunk có nhãn URL/Điều đúng. "
        "Các số này không phải điểm RAGAS/LLM judge hay xác nhận pháp lý.", "",
        "## Worst performers", "",
    ]
    worst = sorted(enumerate(hybrid["rows"], 1), key=lambda pair: (pair[1]["context_recall"], pair[1]["answer_relevance"]))[:5]
    for index, row in worst:
        lines.append(f"- Câu {index}: {row['question']} — context recall {row['context_recall']:.0f}, "
                     f"answer relevance {row['answer_relevance']:.3f}.")
    lines += [
        "", "## Recommendations", "",
        "- Mở rộng corpus theo từng điều và xác minh hiệu lực, sửa đổi văn bản trước khi dùng để tư vấn thực tế.",
        "- Thử bộ reranker và mở rộng câu hỏi golden; đo lại trên cùng tập để kiểm tra mức cải thiện.",
        "- Đánh giá thủ công tính đúng pháp lý và citation; phép đo lexical không phát hiện suy luận sai hoặc thay đổi hiệu lực.",
        "- Cấu hình API key riêng để kiểm thử PageIndex và các LLM provider; nhánh cloud chưa được đo trong báo cáo này.",
        "", "## Reproduce", "", "```bash", "python -m src.task4_chunking_indexing", "python -m src.evaluate", "```", "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    evaluation = evaluate_all()
    write_report(evaluation)
    print(json.dumps({label: item["metrics"] for label, item in evaluation["results"].items()}, ensure_ascii=True))
