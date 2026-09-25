"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

from pathlib import Path
import re
import os
import hashlib
from contextvars import ContextVar
from functools import lru_cache
from dotenv import load_dotenv


load_dotenv()


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local_lsa")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or (
    "nvidia/llama-nemotron-embed-vl-1b-v2:free" if EMBEDDING_PROVIDER == "openrouter"
    else "bge-m3:latest" if EMBEDDING_PROVIDER == "ollama" else "BAAI/bge-m3"
)
EMBEDDING_DIM = 96 if EMBEDDING_PROVIDER == "local_lsa" else None

COLLECTION_NAME = "rag_documents" if EMBEDDING_PROVIDER == "local_lsa" else (
    "rag_" + hashlib.sha256(f"{EMBEDDING_PROVIDER}:{EMBEDDING_MODEL}".encode()).hexdigest()[:16]
)
_EMBED_INPUT_TYPE = ContextVar("embed_input_type", default="search_document")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed both corpus and queries with one configured model."""
    if not texts:
        return []
    if EMBEDDING_PROVIDER == "openrouter":
        return _openrouter_embeddings(texts, input_type=_EMBED_INPUT_TYPE.get())
    if EMBEDDING_PROVIDER == "ollama":
        return _ollama_embeddings(texts)
    if EMBEDDING_PROVIDER == "sentence_transformers":
        return _sentence_model().encode(texts, normalize_embeddings=True).tolist()
    if EMBEDDING_PROVIDER != "local_lsa":
        raise ValueError(f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")
    vectorizer, svd = _local_lsa()
    from sklearn.preprocessing import normalize

    matrix = svd.transform(vectorizer.transform(texts))
    return normalize(matrix).astype(float).tolist()


def embed_query(query: str) -> list[float]:
    """Use the same model and collection dimension, with query task type if supported."""
    token = _EMBED_INPUT_TYPE.set("search_query")
    try:
        return embed_texts([query])[0]
    finally:
        _EMBED_INPUT_TYPE.reset(token)


def _openrouter_embeddings(texts: list[str], *, input_type: str) -> list[list[float]]:
    import requests
    import time

    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter embeddings")
    vectors = []
    for start in range(0, len(texts), 32):
        batch = texts[start:start + 32]
        for attempt in range(4):
            response = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": EMBEDDING_MODEL, "input": batch, "input_type": input_type},
                timeout=60,
            )
            if response.status_code not in {429, 500, 502, 503, 524, 529} or attempt == 3:
                break
            time.sleep(min(30, float(response.headers.get("Retry-After", 2 ** (attempt + 1)))))
        response.raise_for_status()
        data = response.json()["data"]
        if len(data) != len(batch):
            raise RuntimeError("OpenRouter returned an unexpected number of embeddings")
        ordered = sorted(data, key=lambda item: item["index"])
        if [item["index"] for item in ordered] != list(range(len(batch))):
            raise RuntimeError("OpenRouter embedding indices are invalid")
        vectors.extend(item["embedding"] for item in ordered)
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or not dimensions or 0 in dimensions:
        raise RuntimeError("OpenRouter returned inconsistent embedding dimensions")
    return vectors


def _ollama_embeddings(texts: list[str]) -> list[list[float]]:
    """Embed batches with the local Ollama model used by both index and search."""
    import requests

    endpoint = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/embed"
    vectors = []
    for start in range(0, len(texts), 32):
        batch = texts[start:start + 32]
        response = requests.post(
            endpoint, json={"model": EMBEDDING_MODEL, "input": batch}, timeout=180,
        )
        response.raise_for_status()
        embedded = response.json().get("embeddings", [])
        if len(embedded) != len(batch):
            raise RuntimeError("Ollama returned an unexpected number of embeddings")
        vectors.extend(embedded)
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1 or 0 in dimensions:
        raise RuntimeError("Ollama returned inconsistent embedding dimensions")
    return vectors


@lru_cache(maxsize=1)
def _sentence_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _local_lsa():
    """Fit deterministic dense vectors to the same corpus Task 6 searches."""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    corpus = [chunk["content"] for chunk in chunk_documents(load_documents())]
    if len(corpus) < 3:
        raise ValueError("Need at least three chunks for local dense embeddings")
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 4), min_df=2, max_features=12000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(corpus)
    components = min(EMBEDDING_DIM, matrix.shape[0] - 1, matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=components, random_state=42)
    svd.fit(matrix)
    return vectorizer, svd


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative = path.relative_to(STANDARDIZED_DIR)
        if not relative.parts or relative.parts[0] not in {"legal", "news"}:
            continue
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        url_match = re.search(r"^\*\*(?:Nguồn chính thức|Source):\*\*\s*(https?://\S+)", content, re.MULTILINE)
        documents.append({
            "id": relative.as_posix(),
            "content": content,
            "metadata": {
                "source": relative.as_posix(),
                "title": title_match.group(1).strip() if title_match else path.stem,
                "doc_type": relative.parts[0],
                "url": url_match.group(1) if url_match else None,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        index = 0
        # Preserve article boundaries for legal citations.
        sections = re.split(r"(?=^## Điều\s+\d+\.)", document["content"], flags=re.MULTILINE)
        for section in sections:
            article_match = re.match(r"## (Điều\s+\d+)\.", section)
            for content in splitter.split_text(section):
                if not content.strip():
                    continue
                metadata = {**document["metadata"], "chunk_index": index}
                if article_match:
                    metadata["article"] = article_match.group(1)
                chunks.append({
                    "id": f"{document['id']}::chunk-{index}",
                    "content": content,
                    "metadata": metadata,
                })
                index += 1
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    collection = get_collection()
    for start in range(0, len(chunks), 100):
        batch = chunks[start:start + 100]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[{key: value for key, value in chunk["metadata"].items() if value is not None} for chunk in batch],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
