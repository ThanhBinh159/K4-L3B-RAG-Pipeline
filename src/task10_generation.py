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

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.6-flash",
    "anthropic": "claude-sonnet-4-6",
    "openrouter": "google/gemini-3.6-flash",
}


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng (đầu danh sách retrieval) về đầu và cuối context.

    Giảm lost-in-the-middle: LLM chú ý nhiều nhất tới phần đầu/cuối prompt, nên
    chunk có score cao nhất được đặt ở đầu, chunk score cao thứ nhì ở cuối, v.v.
    Không mutate input.
    """
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label để LLM tạo citation kiểm chứng được."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def _call_openai(system_prompt: str, user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = LLM_MODEL or _DEFAULT_MODELS["openai"]
    response = client.chat.completions.create(
        model=model,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


def _call_gemini(system_prompt: str, user_message: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = LLM_MODEL or _DEFAULT_MODELS["gemini"]
    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        ),
    )
    return response.text or ""


def _call_anthropic(system_prompt: str, user_message: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = LLM_MODEL or _DEFAULT_MODELS["anthropic"]
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def _call_openrouter(system_prompt: str, user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    model = LLM_MODEL or "google/gemini-3.6-flash"
    response = client.chat.completions.create(
        model=model,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


def call_llm(system_prompt: str, user_message: str) -> str:
    if LLM_PROVIDER == "openai":
        return _call_openai(system_prompt, user_message)
    if LLM_PROVIDER == "gemini":
        return _call_gemini(system_prompt, user_message)
    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_message)
    if LLM_PROVIDER == "openrouter":
        return _call_openrouter(system_prompt, user_message)
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")

def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception as error:
        print(f"LLM call failed, returning safe refusal: {error}")
        return {
            "answer": SAFE_REFUSAL,
            "sources": chunks,
            "retrieval_source": "none",
        }

    if not answer.strip():
        return {
            "answer": SAFE_REFUSAL,
            "sources": chunks,
            "retrieval_source": "none",
        }

    # retrieve() chỉ bao giờ trả kết quả gắn "hybrid" hoặc "pageindex", nên
    # ánh xạ trực tiếp sang retrieval_source của GenerationResult.
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": "pageindex" if chunks[0]["retrieval_method"] == "pageindex" else "hybrid",
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
