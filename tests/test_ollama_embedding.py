def test_ollama_embeddings_use_local_embed_api(monkeypatch):
    import requests
    import src.task4_chunking_indexing as indexing

    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"embeddings": [[1.0, 0.0], [0.0, 1.0]]}

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setattr(requests, "post", fake_post)
    assert indexing._ollama_embeddings(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert calls[0][0] == "http://localhost:11434/api/embed"
    assert calls[0][1]["json"] == {"model": indexing.EMBEDDING_MODEL, "input": ["a", "b"]}
