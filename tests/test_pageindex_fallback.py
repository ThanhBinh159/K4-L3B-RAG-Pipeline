import json

from src.contracts import validate_search_results


def test_pageindex_tree_nodes_map_to_search_results(monkeypatch, tmp_path):
    import src.task8_pageindex_vectorless as pageindex

    cache = tmp_path / "ids.json"
    cache.write_text(json.dumps({"law.pdf": "doc-1"}), encoding="utf-8")

    class Client:
        def get_tree(self, doc_id, **kwargs):
            assert doc_id == "doc-1"
            assert kwargs == {"node_summary": True, "include_text": True}
            return {"status": "completed", "result": [{
                "node_id": "n1", "title": "Thuế hộ kinh doanh", "nodes": [{
                    "node_id": "n2", "page_index": 2,
                    "text": "Mã số thuế hộ kinh doanh là số định danh cá nhân.",
                }],
            }]}

    monkeypatch.setenv("PAGEINDEX_API_KEY", "test-key")
    monkeypatch.setattr(pageindex, "CACHE_PATH", cache)
    monkeypatch.setattr(pageindex, "upload_documents", lambda: None)
    monkeypatch.setattr(pageindex, "_client", lambda: Client())
    monkeypatch.setattr(pageindex, "_sources", lambda: {"law.pdf": {
        "title": "Luật quản lý thuế", "url": "https://example.vn/law",
    }})
    results = pageindex.pageindex_search("mã số thuế hộ kinh doanh", top_k=3)
    validate_search_results(results, top_k=3, expected_method="pageindex")
    assert results[0]["id"] == "pageindex:doc-1:n2"
    assert results[0]["metadata"]["page_index"] == 2
