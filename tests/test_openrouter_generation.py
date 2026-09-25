from types import SimpleNamespace


def test_call_llm_routes_openrouter_chat_with_configured_key(monkeypatch):
    import openai
    import src.task10_generation as generation

    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["request"] = kwargs
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Có [1]"))])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(generation, "LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(generation, "LLM_MODEL", "nvidia/nemotron-3.5-lightning:free")
    assert generation.call_llm("system", "question") == "Có [1]"
    assert calls["client"]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls["client"]["api_key"] == "test-key"
    assert calls["request"]["model"] == "nvidia/nemotron-3.5-lightning:free"
    assert "top_p" not in calls["request"]
    assert calls["request"]["extra_body"] == {"reasoning": {"enabled": False}}


def test_model_quote_must_match_cited_source_verbatim():
    from src.task10_generation import _validated_model_quote

    sources = [{"content": "Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ."}]
    good = "Theo luật: “Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ.” [1]"
    bad = "Theo luật: “Mã số thuế là mã do cơ quan cấp phép tự tạo.” [1]"
    assert _validated_model_quote(good, sources) == (
        "Theo tài liệu: “Mã số thuế của hộ kinh doanh là số định danh cá nhân của chủ hộ.” [1]"
    )
    assert _validated_model_quote(bad, sources) is None
    assert _validated_model_quote(good.replace("[1]", "[2]"), sources) is None
