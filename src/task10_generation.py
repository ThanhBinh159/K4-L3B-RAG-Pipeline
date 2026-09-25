"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    return list(chunks[::2]) + list(chunks[1::2][::-1])


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | Source: {metadata['source']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi provider LLM theo cấu hình."""
    provider = LLM_PROVIDER.lower()
    if provider == "openrouter":
        import requests
        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"].get("content", "")
    if provider == "deepseek":
        import requests
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"].get("content", "")
    if provider == "openai":
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        client = OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL") or None)
        response = client.chat.completions.create(
            model=LLM_MODEL or "gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""
    if provider == "gemini":
        from google import genai
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=LLM_MODEL or "gemini-2.0-flash",
            contents=user_message,
            config={"system_instruction": system_prompt, "temperature": TEMPERATURE, "top_p": TOP_P},
        )
        return response.text or ""
    if provider == "anthropic":
        from anthropic import Anthropic
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        client = Anthropic(api_key=key)
        response = client.messages.create(
            model=LLM_MODEL or "claude-3-5-haiku-latest",
            max_tokens=1200,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    refusal = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {"answer": refusal, "sources": [], "retrieval_source": "none"}
    try:
        answer = call_llm(
            SYSTEM_PROMPT,
            f"Context:\n{format_context(reorder_for_llm(chunks))}\n\nQuestion: {query}",
        ).strip()
    except Exception:
        answer = refusal
    if not answer:
        answer = refusal
    source = "pageindex" if chunks[0]["retrieval_method"] == "pageindex" else "hybrid"
    return {"answer": answer, "sources": chunks, "retrieval_source": source}


if __name__ == "__main__":
    print(generate_with_citation("test query"))
