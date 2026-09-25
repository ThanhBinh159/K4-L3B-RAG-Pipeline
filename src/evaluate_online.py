"""Run all golden questions through the configured live RAG pipeline.

Writes a checkpoint after each question so a gateway interruption can resume.
The four scores remain deterministic proxy metrics, not an LLM judge.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .contracts import validate_generation_result
from .evaluate import GOLD_PATH, answer_relevance, context_metrics, faithfulness
from .task4_chunking_indexing import EMBEDDING_MODEL, EMBEDDING_PROVIDER
from .task10_generation import LLM_MODEL, LLM_PROVIDER, REFUSAL, generate_with_citation, get_generation_mode


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "group_project" / "evaluation"
RESULTS_PATH = OUTPUT_DIR / "online_results.json"
REPORT_PATH = OUTPUT_DIR / "RESULT_ONLINE.md"
METRICS = ("faithfulness", "answer_relevance", "context_recall", "context_precision")


def evaluate_case_online(case: dict, top_k: int = 5) -> dict:
    started = time.perf_counter()
    result = generate_with_citation(case["question"], top_k=top_k)
    elapsed = time.perf_counter() - started
    validate_generation_result(result)
    sources = result["sources"]
    recall, precision = context_metrics(sources, case)
    return {
        "question": case["question"],
        "answer": result["answer"],
        "generation_mode": get_generation_mode(),
        "retrieval_source": result["retrieval_source"],
        "source_ids": [source["id"] for source in sources],
        "source_urls": [source["metadata"].get("url") for source in sources],
        "source_articles": [source["metadata"].get("article") for source in sources],
        "refusal": result["answer"] == REFUSAL,
        "elapsed_seconds": round(elapsed, 3),
        "faithfulness": faithfulness(result["answer"], sources),
        "answer_relevance": answer_relevance(result["answer"], case["expected_answer"]),
        "context_recall": recall,
        "context_precision": precision,
    }


def _config(top_k: int) -> dict:
    gateway = os.getenv("GEMINI_BASE_URL", "")
    return {
        "dataset_sha256": hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest(),
        "top_k": top_k,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "gemini_gateway_host": urlsplit(gateway).netloc if gateway else None,
    }


def run_online(top_k: int = 5) -> dict:
    cases = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    config = _config(top_k)
    if RESULTS_PATH.exists():
        output = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        if output["config"] != config:
            raise ValueError("Existing online_results.json uses another dataset or configuration")
    else:
        output = {"config": config, "started_at": datetime.now(timezone.utc).isoformat(), "rows": []}
    for index in range(len(output["rows"]), len(cases)):
        row = evaluate_case_online(cases[index], top_k=top_k)
        row["case_index"] = index + 1
        output["rows"].append(row)
        temporary = RESULTS_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(RESULTS_PATH)
        print(json.dumps({"case": index + 1, "of": len(cases), "mode": row["generation_mode"],
                          "faithfulness": row["faithfulness"], "answer_relevance": round(row["answer_relevance"], 3),
                          "seconds": row["elapsed_seconds"]}, ensure_ascii=True), flush=True)
    output["completed_at"] = datetime.now(timezone.utc).isoformat()
    RESULTS_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    write_online_report(output)
    return output


def write_online_report(output: dict) -> None:
    rows = output["rows"]
    if not rows:
        return
    means = {name: sum(row[name] for row in rows) / len(rows) for name in METRICS}
    modes = {mode: sum(row["generation_mode"] == mode for row in rows)
             for mode in sorted({row["generation_mode"] for row in rows})}
    config = output["config"]
    lines = [
        "# Golden dataset: chạy online", "",
        f"Đã chạy {len(rows)} câu hỏi với `top_k={config['top_k']}`; "
        f"embedding `{config['embedding_provider']}` (`{config['embedding_model']}`), "
        f"generation `{config['llm_provider']}` (`{config['llm_model']}`). "
        "Gateway và API key lấy từ `.env`; kết quả không lưu key.", "",
        "## Overall scores", "",
        "| Metric (proxy) | Score |", "| --- | ---: |",
    ]
    lines += [f"| {name} | {means[name]:.3f} |" for name in METRICS]
    lines += [
        "", f"Từ chối: {sum(row['refusal'] for row in rows)}/{len(rows)}. "
        f"Thời gian tổng: {sum(row['elapsed_seconds'] for row in rows):.1f} giây.", "",
        "## Generation modes", "",
    ]
    lines += [f"- `{mode}`: {count} câu" for mode, count in modes.items()]
    lines += [
        "", "`model_quote` là đoạn model chọn và được đối chiếu nguyên văn với source. "
        "`extractive_fallback` hoặc `provider_error_fallback` là câu trích xuất từ corpus khi model không tạo được trích dẫn kiểm chứng được.", "",
        "## Worst performers", "",
    ]
    for row in sorted(rows, key=lambda item: (item["context_recall"], item["answer_relevance"]))[:5]:
        lines.append(f"- Câu {row['case_index']}: {row['question']} — "
                     f"answer relevance {row['answer_relevance']:.3f}, context recall {row['context_recall']:.0f}, "
                     f"mode `{row['generation_mode']}`.")
    lines += [
        "", "## Metric definitions and limits", "",
        "- Faithfulness: phần trích trong câu trả lời xuất hiện ở source được dẫn; đây là kiểm tra văn bản, không phải đánh giá suy luận.",
        "- Answer relevance: token F1 với đáp án tham chiếu.",
        "- Context recall: có ít nhất một chunk đúng URL và đúng Điều nếu golden có nhãn Điều.",
        "- Context precision: average precision@5 theo nhãn URL/Điều.",
        "- Các metric là proxy offline tính trên câu trả lời và kết quả retrieval online; chưa phải RAGAS hoặc xác nhận hiệu lực pháp luật.",
        "- Chi tiết từng câu nằm trong `online_results.json`; báo cáo A/B dense/hybrid riêng ở `RESULT.md`.",
        "", "## Reproduce", "", "```bash", "python -m src.evaluate_online", "```", "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run_online()
