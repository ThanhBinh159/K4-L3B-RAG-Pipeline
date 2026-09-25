from types import SimpleNamespace


def test_gemini_uses_configured_base_url(monkeypatch):
    from google import genai
    import src.task10_generation as generation

    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(text="Theo tài liệu: “Mã số thuế là số định danh cá nhân.” [1]")

    class FakeClient:
        models = FakeModels()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    def fake_client(**kwargs):
        captured["client"] = kwargs
        return FakeClient()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "http://localhost:8317")
    monkeypatch.setattr(genai, "Client", fake_client)
    monkeypatch.setattr(generation, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(generation, "LLM_MODEL", "gemini-3.1-flash-lite")

    assert "Mã số thuế" in generation.call_llm("system", "question")
    assert captured["client"]["api_key"] == "test-key"
    assert captured["client"]["http_options"].base_url == "http://localhost:8317"
    assert captured["request"]["model"] == "gemini-3.1-flash-lite"


def test_generation_keeps_only_verifiable_quote(monkeypatch):
    import src.task10_generation as generation

    chunk = {
        "id": "law::chunk-0",
        "content": "Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ.",
        "score": 0.8,
        "retrieval_method": "hybrid",
        "metadata": {
            "source": "law.md", "title": "Luật quản lý thuế", "doc_type": "legal",
            "url": "https://example.vn/law", "chunk_index": 0,
        },
    }
    monkeypatch.setattr(generation, "retrieve", lambda query, top_k: [chunk])
    monkeypatch.setattr(generation, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(
        generation, "call_llm",
        lambda system, user: "Mã này do cơ quan tự tạo. Theo tài liệu: “Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ.” [1]",
    )
    result = generation.generate_with_citation("Mã số thuế hộ kinh doanh là gì?")
    assert result["answer"] == "Theo tài liệu: “Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ.” [1]"
    assert result["sources"] == [chunk]
