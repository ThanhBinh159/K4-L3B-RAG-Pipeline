import pytest


def test_openrouter_embeddings_preserve_response_index_and_task_type(monkeypatch):
    import src.task4_chunking_indexing as indexing
    import requests

    calls = []

    class Response:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [
                {"index": 1, "embedding": [0.0, 1.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ]}

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(requests, "post", fake_post)
    vectors = indexing._openrouter_embeddings(["a", "b"], input_type="search_document")
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert calls[0][1]["json"]["model"] == indexing.EMBEDDING_MODEL
    assert calls[0][1]["json"]["input_type"] == "search_document"
    assert calls[0][1]["timeout"] == 60


def test_openrouter_requires_key(monkeypatch):
    import src.task4_chunking_indexing as indexing

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        indexing._openrouter_embeddings(["a"], input_type="search_query")
