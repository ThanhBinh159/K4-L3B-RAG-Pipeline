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

import hashlib
import json
import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document

load_dotenv()


STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hash").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b:free")
EMBEDDING_DIM = 1024
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"

_MODEL_KEY = re.sub(r"[^a-zA-Z0-9]+", "_", EMBEDDING_MODEL).strip("_").lower()
COLLECTION_NAME = os.getenv("COLLECTION_NAME", f"rag_documents_{EMBEDDING_PROVIDER}_{_MODEL_KEY}")
FALLBACK_INDEX_PATH = CHROMA_DIR / f"{COLLECTION_NAME}.json"


class _JsonCollection:
    """Small offline store used only when optional ChromaDB is unavailable."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def upsert(self, *, ids, documents, embeddings, metadatas) -> None:
        self.rows.update({
            item_id: {"document": document, "embedding": embedding, "metadata": metadata}
            for item_id, document, embedding, metadata in zip(ids, documents, embeddings, metadatas)
        })
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.rows, ensure_ascii=False), encoding="utf-8")

    def query(self, *, query_embeddings, n_results, include):
        query = query_embeddings[0]
        ranked = sorted(
            self.rows.items(),
            key=lambda pair: sum(a * b for a, b in zip(query, pair[1]["embedding"])),
            reverse=True,
        )[:n_results]
        return {
            "ids": [[item_id for item_id, _ in ranked]],
            "documents": [[row["document"] for _, row in ranked]],
            "metadatas": [[row["metadata"] for _, row in ranked]],
            "distances": [[1 - sum(a * b for a, b in zip(query, row["embedding"])) for _, row in ranked]],
        }


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create deterministic offline vectors shared by indexing and search.

    Set ``EMBEDDING_PROVIDER=sentence-transformers`` only when that optional
    package/model is installed; the default hash encoder keeps the lab runnable
    without a network or API key.
    """
    if not texts:
        return []
    if EMBEDDING_PROVIDER == "openrouter":
        import requests
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        response = requests.post(
            OPENROUTER_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": EMBEDDING_MODEL, "input": texts},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        if len(vectors) != len(texts):
            raise RuntimeError("OpenRouter returned an incomplete embedding batch")
        return vectors
    if EMBEDDING_PROVIDER == "sentence-transformers":
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        return model.encode(texts, normalize_embeddings=True).tolist()

    vectors = []
    for text in texts:
        vector = [0.0] * EMBEDDING_DIM
        for token in re.findall(r"\w+", text.lower(), flags=re.UNICODE):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        vectors.append([value / norm for value in vector])
    return vectors


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    try:
        import chromadb
    except ImportError:
        return _JsonCollection(FALLBACK_INDEX_PATH)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")) if STANDARDIZED_DIR.exists() else []:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        doc_type = "legal" if "legal" in path.parts else "news"
        document = {
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": path.stem,
                "doc_type": doc_type,
                "url": None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    chunks = []
    for document in documents:
        validate_document(document)
        text = document["content"].strip()
        start = 0
        index = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            if end < len(text):
                boundary = max(text.rfind(separator, start + 1, end) for separator in ("\n\n", "\n", ". ", " "))
                if boundary > start:
                    end = boundary + (2 if text[boundary:boundary + 2] == "\n\n" else 1)
            piece = text[start:end].strip()
            if piece:
                chunks.append({
                    "id": f"{document['id']}::chunk-{index}",
                    "content": piece,
                    "metadata": {**document["metadata"], "chunk_index": index},
                })
                index += 1
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    return [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[{key: (value if value is not None else "") for key, value in chunk["metadata"].items()} for chunk in chunks],
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
