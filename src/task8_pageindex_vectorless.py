"""Optional PageIndex tree retrieval over the official legal PDFs.

The SDK indexes PDFs; ranking the returned tree nodes uses word overlap and no
vector embedding. With no PageIndex key the fallback is unavailable.
"""

import json
import os
import re
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "landing" / "legal"
CACHE_PATH = ROOT / "pageindex_doc_ids.json"
MANIFEST_PATH = ROOT / "data" / "standardized" / "legal" / "hkd_manifest.json"


@lru_cache(maxsize=1)
def _client():
    from pageindex import PageIndexClient

    return PageIndexClient(index="cloud", chat=os.getenv("PAGEINDEX_CHAT_MODEL", "gpt-4o-mini"))


def _sources() -> dict[str, dict]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sources = {}
    for pdf in PDF_DIR.glob("*.pdf"):
        match = re.search(r"(\d+_\d{4})", pdf.stem)
        if not match:
            continue
        number, year = match.group(1).split("_")
        item = next((doc for doc in manifest["documents"] if f"_{number}_{year}.md" in doc["file"]), None)
        if item:
            sources[pdf.name] = {"title": item["title"], "url": item["source_url"]}
    return sources


def upload_documents() -> None:
    """Upload missing legal PDFs and cache their PageIndex document IDs."""
    if not os.getenv("PAGEINDEX_API_KEY"):
        return
    cached = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    client = _client()
    for name in sorted(_sources()):
        if name in cached:
            continue
        doc_id = client.submit_document(str(PDF_DIR / name), wait=True)["doc_id"]
        cached[name] = doc_id
        CACHE_PATH.write_text(json.dumps(cached, ensure_ascii=False, indent=2), encoding="utf-8")


def _nodes(tree):
    for node in tree if isinstance(tree, list) else [tree]:
        if not isinstance(node, dict):
            continue
        if node.get("text"):
            yield node
        yield from _nodes(node.get("nodes", []))


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Rank PageIndex tree nodes and return SearchResult records."""
    if not query.strip() or top_k <= 0 or not os.getenv("PAGEINDEX_API_KEY"):
        return []
    upload_documents()
    cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    sources = _sources()
    terms = set(re.findall(r"[^\W_]+", query.casefold()))
    results = []
    for name, doc_id in cached.items():
        if name not in sources:
            continue
        tree = _client().get_tree(doc_id, node_summary=True, include_text=True)
        if tree.get("status") != "completed":
            continue
        for index, node in enumerate(_nodes(tree.get("result", []))):
            content = node["text"].strip()
            node_terms = set(re.findall(r"[^\W_]+", (node.get("title", "") + " " + content).casefold()))
            score = len(terms & node_terms) / max(1, len(terms))
            if not content or score <= 0:
                continue
            results.append({
                "id": f"pageindex:{doc_id}:{node.get('node_id', index)}",
                "content": content,
                "score": float(score),
                "metadata": {
                    "source": name, "title": sources[name]["title"], "doc_type": "legal",
                    "url": sources[name]["url"], "chunk_index": index,
                    "page_index": node.get("page_index", 0),
                },
                "retrieval_method": "pageindex",
            })
    return sorted(results, key=lambda item: (-item["score"], item["id"]))[:top_k]


if __name__ == "__main__":
    upload_documents()
