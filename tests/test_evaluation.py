from src.evaluate import answer_relevance, context_metrics, faithfulness


def test_faithfulness_requires_quote_in_cited_source():
    sources = [{"content": "Hộ kinh doanh dùng mã số định danh cá nhân."}]
    assert faithfulness("Theo nguồn: “Hộ kinh doanh dùng mã số định danh cá nhân.” [1]", sources) == 1
    assert faithfulness("Theo nguồn: “Có thể không cần mã số.” [1]", sources) == 0
    assert faithfulness("Theo nguồn: “Hộ kinh doanh dùng mã số định danh cá nhân.” [2]", sources) == 0


def test_context_metrics_require_source_and_article():
    case = {"source_url": "https://example.vn/law", "article": "Điều 11"}
    sources = [
        {"metadata": {"url": "https://example.vn/law", "article": "Điều 10"}},
        {"metadata": {"url": "https://example.vn/law", "article": "Điều 11"}},
    ]
    assert context_metrics(sources, case) == (1, 0.5)


def test_answer_relevance_uses_reference_tokens():
    assert answer_relevance("Mã số thuế là số định danh. [1]", "Mã số thuế là số định danh.") == 1
    assert answer_relevance("Tôi không thể xác minh thông tin này từ nguồn hiện có.", "Mã số thuế") == 0


def test_ab_uses_same_questions_and_changes_only_retrieval_mode(monkeypatch, tmp_path):
    import json
    import src.evaluate as evaluation

    cases = [{"question": "Câu hỏi 1"}, {"question": "Câu hỏi 2"}]
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(cases), encoding="utf-8")
    monkeypatch.setattr(evaluation, "GOLD_PATH", gold)
    calls = []

    def fake_case(case, *, hybrid):
        calls.append((case["question"], hybrid))
        return {"faithfulness": 1.0, "answer_relevance": 0.5,
                "context_recall": 1.0, "context_precision": 0.5}

    monkeypatch.setattr(evaluation, "evaluate_case", fake_case)
    evaluation.evaluate_all()
    assert calls == [("Câu hỏi 1", False), ("Câu hỏi 2", False),
                     ("Câu hỏi 1", True), ("Câu hỏi 2", True)]
