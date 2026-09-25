import asyncio
import json


def test_pdf_link_parser_decodes_official_download_url():
    from src.task1_collect_legal_docs import find_pdf_url

    html = '<a href="https://cdn.example/download?x=1&amp;file_name=law.pdf">PDF</a>'
    assert find_pdf_url(html, "https://official.example/page") == "https://cdn.example/download?x=1&file_name=law.pdf"


def test_article_extraction_keeps_only_body_and_metadata():
    from src.task2_crawl_news import extract_article

    html = """<html><h1>Đăng ký hộ kinh doanh</h1>
    <div class='detail-content afcbc-body'><p>Nộp hồ sơ tại cơ quan đăng ký cấp xã.</p>
    <p>Tham khảo thêm bài khác</p><h2>Bài khác</h2></div></html>"""
    item = extract_article(html, "https://example.org/guide", "2026-09-25")
    assert item["title"] == "Đăng ký hộ kinh doanh"
    assert "Nộp hồ sơ" in item["content_markdown"]
    assert "Tham khảo thêm" not in item["content_markdown"]


def test_news_conversion_preserves_source_and_is_idempotent(tmp_path, monkeypatch):
    import src.task3_convert_markdown as convert

    landing = tmp_path / "landing"
    output = tmp_path / "standardized"
    (landing / "news").mkdir(parents=True)
    item = {
        "url": "https://example.org/guide",
        "title": "Hướng dẫn",
        "date_crawled": "2026-09-25",
        "content_markdown": "Nội dung về hộ kinh doanh.",
    }
    (landing / "news" / "guide.json").write_text(json.dumps(item), encoding="utf-8")
    monkeypatch.setattr(convert, "LANDING_DIR", landing)
    monkeypatch.setattr(convert, "OUTPUT_DIR", output)
    convert.convert_news_articles()
    first = (output / "news" / "guide.md").read_text(encoding="utf-8")
    convert.convert_news_articles()
    assert (output / "news" / "guide.md").read_text(encoding="utf-8") == first
    assert "https://example.org/guide" in first
