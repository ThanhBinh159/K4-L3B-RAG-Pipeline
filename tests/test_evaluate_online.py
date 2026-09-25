from src.contracts import validate_generation_result


def test_online_case_scores_actual_generated_answer(monkeypatch):
    import src.evaluate_online as online

    result = {
        "answer": "Theo tài liệu: “Mã số thuế là số định danh cá nhân.” [1]",
        "sources": [{
            "id": "law::chunk-0", "content": "Mã số thuế là số định danh cá nhân.",
            "score": 0.5, "retrieval_method": "hybrid",
            "metadata": {
                "source": "law.md", "title": "Luật", "doc_type": "legal",
                "url": "https://example.vn/law", "chunk_index": 0, "article": "Điều 11",
            },
        }],
        "retrieval_source": "hybrid",
    }
    validate_generation_result(result)
    monkeypatch.setattr(online, "generate_with_citation", lambda question, top_k: result)
    case = {
        "question": "Mã số thuế là gì?", "expected_answer": "Mã số thuế là số định danh cá nhân.",
        "source_url": "https://example.vn/law", "article": "Điều 11",
    }
    row = online.evaluate_case_online(case, top_k=3)
    assert row["answer"] == result["answer"]
    assert row["faithfulness"] == 1.0
    assert row["context_recall"] == 1.0
    assert row["context_precision"] == 1.0
    assert row["source_ids"] == ["law::chunk-0"]
