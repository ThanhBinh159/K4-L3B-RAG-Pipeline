from src.prepare_household_business_corpus import render_law_markdown, select_articles


def test_loader_uses_law_and_article_sources(tmp_path, monkeypatch):
    import src.task4_chunking_indexing as indexing

    legal = tmp_path / "legal"
    news = tmp_path / "news"
    legal.mkdir()
    news.mkdir()
    (legal / "law.md").write_text(
        "# Luật mẫu\n\n**Nguồn chính thức:** https://official.example/law\n\n## Điều 1\nNội dung luật.",
        encoding="utf-8",
    )
    (news / "guide.md").write_text(
        "# Hướng dẫn\n\n**Source:** https://official.example/guide\n\nNội dung hướng dẫn.",
        encoding="utf-8",
    )
    monkeypatch.setattr(indexing, "STANDARDIZED_DIR", tmp_path)
    loaded = indexing.load_documents()
    assert len(loaded) == 2
    by_type = {item["metadata"]["doc_type"]: item for item in loaded}
    assert by_type["legal"]["metadata"]["url"] == "https://official.example/law"
    assert by_type["news"]["metadata"]["url"] == "https://official.example/guide"


def test_selection_deduplicates_sources_and_rejects_broken_article_splits():
    base = {
        "instrument_id": "vn-law-1",
        "instrument_title": "Luật mẫu",
        "article_number": "Điều 1",
        "article_title": "Điều 1. Phạm vi điều chỉnh",
        "body": "Điều 1. Phạm vi điều chỉnh. Nội dung về hộ kinh doanh.",
        "source_url": "https://official.example/law",
        "entry_cid": "cid-a",
        "source_revision": "revision-a",
        "snapshot_date": "2026-09-08",
    }
    duplicate = {**base, "source_url": "https://official.example/duplicate"}
    broken = {**base, "article_number": "Điều 2", "article_title": "Điều 2 của Luật khác", "body": "Điều 2 của Luật khác là một trích dẫn."}
    selected = select_articles([broken, duplicate, base], {"vn-law-1": {1, 2}})
    assert len(selected["vn-law-1"]) == 1
    assert selected["vn-law-1"][0]["source_url"] == base["source_url"]


def test_rendered_law_keeps_article_and_citation_metadata():
    row = {
        "instrument_id": "vn-law-1",
        "instrument_title": "Luật mẫu",
        "article_number": "Điều 1",
        "article_title": "Điều 1. Phạm vi điều chỉnh",
        "body": "Điều 1. Phạm vi điều chỉnh. Nội dung về hộ kinh doanh.",
        "source_url": "https://official.example/law",
        "entry_cid": "cid-a",
        "source_revision": "revision-a",
        "snapshot_date": "2026-09-08",
    }
    text = render_law_markdown([row], dataset_revision="revision-b")
    assert "https://official.example/law" in text
    assert "revision-b" in text
    assert "cid-a" in text
    assert "Điều 1. Phạm vi điều chỉnh" in text
