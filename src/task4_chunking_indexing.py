"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn (recursive character splitting).
    3. Embed chunks bằng một provider duy nhất (EMBEDDING_PROVIDER trong .env).
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng (dùng path tương đối + chunk index
làm id -> upsert theo id cũ sẽ ghi đè thay vì nhân bản). Task 5 phải dùng
chung embed_texts().
"""

import os
from pathlib import Path
import time
from dotenv import load_dotenv


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")


COLLECTION_NAME = "rag_documents"

_sentence_transformer_cache: dict[str, object] = {}


def _embed_with_sentence_transformers(texts: list[str]) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = _sentence_transformer_cache.get("model")
    if model is None or _sentence_transformer_cache.get("name") != EMBEDDING_MODEL:
        model = SentenceTransformer(EMBEDDING_MODEL)
        _sentence_transformer_cache["model"] = model
        _sentence_transformer_cache["name"] = EMBEDDING_MODEL
    return model.encode(texts, normalize_embeddings=True).tolist()


def _embed_with_openai(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = EMBEDDING_MODEL if EMBEDDING_MODEL else "text-embedding-3-small"
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _embed_with_gemini(texts: list[str]) -> list[list[float]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = EMBEDDING_MODEL if EMBEDDING_MODEL else "gemini-embedding-001"

    result: list[list[float]] = []
    batch_size = 50  # giảm xuống 50

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model=model,
            contents=[
                types.Content(parts=[types.Part(text=t)])
                for t in batch
            ],
        )
        if not response.embeddings:
            raise RuntimeError(
                f"Gemini embedding trả về rỗng cho batch {i}-{i+len(batch)}"
            )
        result.extend([emb.values for emb in response.embeddings])

        # delay giữa các batch để tránh 429
        if i + batch_size < len(texts):
            time.sleep(1.2)

    return result 

def _embed_with_openrouter(texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    model = EMBEDDING_MODEL if EMBEDDING_MODEL else "openai/text-embedding-3-small"
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if EMBEDDING_PROVIDER == "sentence_transformers":
        return _embed_with_sentence_transformers(texts)
    if EMBEDDING_PROVIDER == "openai":
        return _embed_with_openai(texts)
    if EMBEDDING_PROVIDER == "gemini":
        return _embed_with_gemini(texts)
    if EMBEDDING_PROVIDER == "openrouter":
        return _embed_with_openrouter(texts)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


def get_collection():
    """Mở Chroma collection dùng cosine distance (persistent, tự tạo nếu chưa có)."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc mọi .md trong data/standardized/ và trả về danh sách Document."""
    documents = []
    if not STANDARDIZED_DIR.is_dir():
        return documents

    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        doc_type = "legal" if "legal" in path.parts else "news"
        documents.append(
            {
                "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
                "content": content,
                "metadata": {
                    "source": path.name,
                    "title": path.stem,
                    "doc_type": doc_type,
                    "url": None,
                },
            }
        )
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id ổn định và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        for index, text in enumerate(splitter.split_text(document["content"])):
            text = text.strip()
            if not text:
                continue
            chunks.append(
                {
                    "id": f"{document['id']}::chunk-{index}",
                    "content": text,
                    "metadata": {**document["metadata"], "chunk_index": index},
                }
            )
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError(
            f"Số vector ({len(vectors)}) != số chunk ({len(chunks)}). "
            f"Kiểm tra lại EMBEDDING_PROVIDER={EMBEDDING_PROVIDER}"
        )
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks

def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB (upsert theo id -> chạy lại không nhân bản)."""
    if not chunks:
        print("No chunks to index.")
        return
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    if not documents:
        print(f"Không tìm thấy Markdown trong {STANDARDIZED_DIR}. Chạy Task 3 trước.")
        return
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
