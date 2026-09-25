from src.task6_lexical_search import lexical_search


def _chunk(item_id, source, url, content, score=0.5, method="hybrid"):
    return {
        "id": item_id,
        "content": content,
        "score": score,
        "metadata": {
            "source": source,
            "title": source.rsplit("/", 1)[-1],
            "doc_type": "news",
            "url": url,
            "chunk_index": int(item_id.rsplit("-", 1)[-1]),
        },
        "retrieval_method": method,
    }


def test_lexical_search_ranks_exact_form_over_generic_household_business_terms(monkeypatch):
    import src.task6_lexical_search as lexical

    corpus = [
        _chunk(
            "news-0", "news/forms.md", "https://example.vn/forms",
            "Chi tiết 28 biểu mẫu đăng ký hộ kinh doanh. Mẫu số 1: Giấy đề nghị đăng ký hộ kinh doanh.",
        ),
        _chunk(
            "tax-0", "news/tax.md", "https://example.vn/tax",
            "Hộ kinh doanh cần thông báo doanh thu năm 2026 và thực hiện nghĩa vụ thuế.",
        ),
    ]
    monkeypatch.setattr(lexical, "CORPUS", corpus)

    results = lexical_search("Theo danh sách biểu mẫu năm 2026, mẫu số 1 dùng để làm gì?", top_k=2)

    assert results[0]["id"] == "news-0"


def test_lexical_tokenizer_preserves_numbered_form_as_one_search_anchor():
    from src.task6_lexical_search import _tokens

    assert "mẫu_số_1" in _tokens("Theo danh sách, Mẫu số 1 dùng để làm gì?")


def test_numbered_form_anchor_does_not_treat_form_01_as_form_1():
    from src.task9_retrieval_pipeline import _matches_query_anchors

    assert not _matches_query_anchors("Mẫu số 1 dùng để làm gì?", "Mẫu số 01/TKN-CNKD")


def test_lexical_search_does_not_return_documents_without_query_term_overlap(monkeypatch):
    import src.task6_lexical_search as lexical

    corpus = [
        _chunk("tax-0", "news/tax.md", "https://example.vn/tax", "Khai thuế hộ kinh doanh."),
    ]
    monkeypatch.setattr(lexical, "CORPUS", corpus)

    assert lexical_search("Mẫu số 1 giấy đề nghị đăng ký", top_k=5) == []


def test_retrieve_groups_duplicate_urls_and_filters_other_sources_for_named_form(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    form_a = _chunk(
        "form-0", "news/forms.md", "https://example.vn/forms?from=search",
        "Mẫu số 1: Giấy đề nghị đăng ký hộ kinh doanh.", 0.04,
    )
    form_b = _chunk(
        "form-1", "news/forms.md", "https://example.vn/forms",
        "Hồ sơ đăng ký hộ kinh doanh nộp tại cơ quan đăng ký cấp xã.", 0.03,
    )
    tax = _chunk(
        "tax-0", "news/tax.md", "https://example.vn/tax",
        "Mẫu 01/TKN-CNKD là thông báo doanh thu của hộ kinh doanh.", 0.02,
    )
    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: [form_a, tax])
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: [form_b, form_a, tax])
    monkeypatch.setattr(pipeline, "rerank_rrf", lambda lists, top_k: [form_a, form_b, tax])
    monkeypatch.setattr(pipeline, "pageindex_search", lambda query, top_k: [])

    results = pipeline.retrieve("Mẫu số 1 dùng để làm gì?", top_k=3, score_threshold=0.0)

    assert [item["metadata"]["url"] for item in results] == ["https://example.vn/forms"]
    assert "Mẫu số 1" in results[0]["content"]
    assert "Hồ sơ đăng ký" in results[0]["content"]


def test_generation_numbers_one_citation_per_merged_source(monkeypatch):
    import src.task10_generation as generation

    source = _chunk(
        "form-0", "news/forms.md", "https://example.vn/forms",
        "Mẫu số 1: Giấy đề nghị đăng ký hộ kinh doanh.\n\n"
        "Hồ sơ đăng ký hộ kinh doanh nộp tại cơ quan đăng ký cấp xã.",
    )
    monkeypatch.setattr(generation, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [source])
    monkeypatch.setattr(
        generation, "call_llm",
        lambda system, message: "Theo tài liệu: “Mẫu số 1: Giấy đề nghị đăng ký hộ kinh doanh.” [1]",
    )

    result = generation.generate_with_citation("Mẫu số 1 dùng để làm gì?")

    assert result["answer"].endswith("[1]")
    assert len(result["sources"]) == 1
