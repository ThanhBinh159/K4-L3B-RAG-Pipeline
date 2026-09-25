"""Grounded answers with citations to the retrieved source records."""

import logging
import os
import re
from contextvars import ContextVar

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()
TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "extractive").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")
REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
DOMAIN_TERMS = {"thuế", "kinh", "doanh", "hộ", "hóa", "đơn", "gtgt", "tncn", "sản", "phẩm", "tiêu", "dùng", "thực", "đăng", "ký", "khiếu", "nại", "sổ", "mẫu", "giấy", "phép", "lệ", "phí", "chứng", "nhận", "lao", "động"}
SYSTEM_PROMPT = (
    "Trả lời bằng tiếng Việt chỉ từ context. Chọn một câu hoặc một mệnh đề liên tục "
    "và chép NGUYÊN VĂN từ một tài liệu. Chỉ xuất đúng định dạng: "
    "Theo tài liệu: “<đoạn nguyên văn>” [số]. Không thêm diễn giải hay khẳng định khác. "
    f"Nếu không đủ chứng cứ, trả lời đúng câu: {REFUSAL}"
)
logger = logging.getLogger(__name__)
_GENERATION_MODE = ContextVar("generation_mode", default="unknown")


def get_generation_mode() -> str:
    """Diagnostic for the most recent answer in the current execution context."""
    return _GENERATION_MODE.get()


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    if len(chunks) <= 2:
        return list(chunks)
    return chunks[::2] + chunks[1::2][::-1]


def format_context(chunks: list[dict]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        citation = chunk.get("citation_index", index)
        parts.append(
            f"[{citation}] Title: {metadata['title']} | Source: {metadata['source']} | "
            f"Article: {metadata.get('article', '')} | URL: {metadata.get('url') or ''}\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    if LLM_PROVIDER == "openrouter":
        from openai import OpenAI

        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is missing")
        response = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", timeout=45).chat.completions.create(
            model=LLM_MODEL or "nvidia/nemotron-3.5-lightning:free", max_tokens=1000,
            extra_body={"reasoning": {"enabled": False}},
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        )
        return response.choices[0].message.content or ""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is missing")
        response = OpenAI(timeout=30).chat.completions.create(
            model=LLM_MODEL or "gpt-4o-mini", temperature=TEMPERATURE, top_p=TOP_P,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        )
        return response.choices[0].message.content or ""
    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types

        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is missing")
        client_options = {"api_key": os.getenv("GEMINI_API_KEY")}
        if os.getenv("GEMINI_BASE_URL"):
            client_options["http_options"] = types.HttpOptions(
                base_url=os.environ["GEMINI_BASE_URL"], timeout=60000,
            )
        with genai.Client(**client_options) as client:
            response = client.models.generate_content(
                model=LLM_MODEL or "gemini-2.5-flash", contents=user_message,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=TEMPERATURE),
            )
        return response.text or ""
    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is missing")
        response = Anthropic(timeout=30).messages.create(
            model=LLM_MODEL or "claude-sonnet-4-5", max_tokens=700, temperature=TEMPERATURE,
            system=system_prompt, messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
    raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")


def _tokens(text: str) -> set[str]:
    stop = {"theo", "điều", "luật", "của", "cho", "và", "nào", "bao", "nhiêu", "thế", "được", "trong", "khi", "một", "có", "là", "gì", "về", "với", "cần", "phải", "như"}
    return {term for term in re.findall(r"[^\W_]+", text.casefold()) if len(term) > 1 and term not in stop}


def _extract_answer(query: str, chunks: list[dict]) -> tuple[str, list[dict]]:
    terms = _tokens(query)
    if not terms or not (terms & DOMAIN_TERMS):
        return REFUSAL, []
    article_match = re.search(r"\bĐiều\s+(\d+)\b", query, flags=re.IGNORECASE)
    article = f"Điều {article_match.group(1)}" if article_match else None
    if article and any(chunk["metadata"].get("article") == article for chunk in chunks):
        eligible = [(index, chunk) for index, chunk in enumerate(chunks, 1)
                    if chunk["metadata"].get("article") == article]
    else:
        eligible = list(enumerate(chunks, 1))
    form_match = re.search(r"\bmẫu\s+số\s+(\d+)\b", query, flags=re.IGNORECASE)
    form_phrase = f"mẫu số {form_match.group(1)}" if form_match else None
    candidates = []
    for index, chunk in eligible:
        metadata = chunk["metadata"]
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", chunk["content"]):
            sentence = sentence.strip(" #*-\t")
            if len(sentence) < 30:
                continue
            overlap = len(terms & _tokens(sentence + " " + metadata["title"] + " " + metadata.get("article", ""))) / len(terms)
            exact_form = bool(form_phrase and re.search(rf"\b{re.escape(form_phrase)}\b", sentence, flags=re.IGNORECASE))
            candidates.append((exact_form, overlap, index, sentence))
    if not candidates:
        return REFUSAL, []
    exact_form, overlap, index, sentence = max(candidates, key=lambda item: (item[0], item[1], -item[2]))
    if overlap < 0.35 and not exact_form:
        return REFUSAL, []
    sentence = sentence[:450].rstrip()
    if len(sentence) == 450:
        sentence += "…"
    return f"Theo tài liệu: “{sentence}” [{index}]", chunks


def _validated_model_quote(answer: str, chunks: list[dict]) -> str | None:
    """Keep only a quote that can be located in its numbered source."""
    for match in re.finditer(r'[“"](.+?)[”"]\s*\[(\d+)\]', answer, flags=re.DOTALL):
        quote = match.group(1).strip()
        index = int(match.group(2))
        if not (1 <= index <= len(chunks)) or len(quote) < 20:
            continue
        source = chunks[index - 1]["content"]
        if " ".join(quote.split()) in " ".join(source.split()):
            return f"Theo tài liệu: “{quote}” [{index}]"
    return None


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    _GENERATION_MODE.set("unknown")
    if not query.strip() or not (_tokens(query) & DOMAIN_TERMS):
        _GENERATION_MODE.set("out_of_domain_refusal")
        return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}
    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        logger.exception("Retrieval failed")
        _GENERATION_MODE.set("retrieval_failure")
        return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}
    if not chunks:
        _GENERATION_MODE.set("no_context")
        return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}
    if LLM_PROVIDER == "extractive":
        answer, cited_sources = _extract_answer(query, chunks)
        _GENERATION_MODE.set("extractive" if cited_sources else "insufficient_evidence")
    else:
        reordered = reorder_for_llm([{**chunk, "citation_index": index} for index, chunk in enumerate(chunks, 1)])
        message = f"Context:\n{format_context(reordered)}\n\nQuestion: {query}"
        try:
            model_answer = call_llm(SYSTEM_PROMPT, message).strip()
            answer = _validated_model_quote(model_answer, chunks)
            if answer is None:
                logger.warning("Generation response lacked a verifiable source quote; using extractive answer")
                answer, _ = _extract_answer(query, chunks)
                _GENERATION_MODE.set("extractive_fallback")
            else:
                _GENERATION_MODE.set("model_quote")
        except Exception:
            logger.exception("Generation provider failed")
            answer, _ = _extract_answer(query, chunks)
            _GENERATION_MODE.set("provider_error_fallback")
        cited_sources = chunks if answer != REFUSAL else []
    return {
        "answer": answer,
        "sources": cited_sources,
        "retrieval_source": chunks[0]["retrieval_method"] if cited_sources and chunks[0]["retrieval_method"] == "pageindex" else ("hybrid" if cited_sources else "none"),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(generate_with_citation("Mã số thuế của hộ kinh doanh là gì?"), ensure_ascii=True))
