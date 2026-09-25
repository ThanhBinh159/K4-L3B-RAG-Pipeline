import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).parent
GOLDEN_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
load_dotenv(ROOT / ".env", override=True)

st.set_page_config(page_title="RAG Pipeline", page_icon="📚", layout="wide")


def load_golden_dataset() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def same_source(expected: str, actual: str) -> bool:
    """Match the same source across landing (.json/.pdf) and Markdown output."""
    return Path(expected).stem.lower() == Path(actual).stem.lower()


def run_embedding() -> dict:
    from src.task4_chunking_indexing import (
        COLLECTION_NAME,
        EMBEDDING_DIM,
        EMBEDDING_MODEL,
        EMBEDDING_PROVIDER,
        chunk_documents,
        embed_chunks,
        index_to_vectorstore,
        load_documents,
    )

    documents = load_documents()
    embedded = embed_chunks(chunk_documents(documents))
    index_to_vectorstore(embedded)
    return {
        "documents": len(documents),
        "chunks": len(embedded),
        "provider": EMBEDDING_PROVIDER,
        "model": EMBEDDING_MODEL,
        "dimension": len(embedded[0]["embedding"]) if embedded else EMBEDDING_DIM,
        "collection": COLLECTION_NAME,
    }


def run_golden(top_k: int) -> list[dict]:
    from src.task9_retrieval_pipeline import retrieve

    report = []
    for case in load_golden_dataset():
        hits = retrieve(case["question"], top_k=top_k)
        sources = [item["metadata"].get("source", "") for item in hits]
        matched = any(same_source(case["expected_context"], source) for source in sources)
        report.append({
            "question": case["question"],
            "expected_context": case["expected_context"],
            "top_source": sources[0] if sources else "-",
            "retrieved_sources": ", ".join(sources) or "-",
            "score": hits[0]["score"] if hits else 0.0,
            "hit": matched,
        })
    return report


def show_sources(sources: list[dict]) -> None:
    if not sources:
        st.info("Không tìm thấy nguồn phù hợp.")
        return
    for index, source in enumerate(sources, 1):
        metadata = source["metadata"]
        with st.expander(f"{index}. {metadata.get('title', metadata.get('source', 'Source'))}"):
            st.caption(f"{metadata.get('source', '-')} · score {source.get('score', 0):.4f}")
            st.markdown(source["content"])


st.title("RAG Pipeline")
st.caption("Chạy embedding, kiểm tra golden dataset và thử truy vấn trên corpus local.")

with st.sidebar:
    st.header("Cấu hình")
    top_k = st.slider("Số chunks", 1, 10, 5)
    st.caption(f"LLM: {os.getenv('LLM_PROVIDER', 'deepseek')} / {os.getenv('LLM_MODEL', 'deepseek-v4-flash')}")
    st.caption(f"Embedding: {os.getenv('EMBEDDING_PROVIDER', 'hash')} / {os.getenv('EMBEDDING_MODEL', 'local-hash-1024')}")

chat_tab, golden_tab, embedding_tab = st.tabs(["Chat", "Golden dataset", "Embedding / index"])

with chat_tab:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                show_sources(message["sources"])

    query = st.chat_input("Nhập câu hỏi...")
    if query:
        from src.task10_generation import generate_with_citation

        st.session_state.messages.append({"role": "user", "content": query})
        result = generate_with_citation(query, top_k=top_k)
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        })
        st.rerun()

with golden_tab:
    dataset = load_golden_dataset()
    st.metric("Golden cases", len(dataset))
    st.write("Case đạt khi expected_context xuất hiện trong top-k nguồn retrieval.")
    if st.button("▶ Chạy golden dataset", type="primary"):
        with st.spinner("Đang chạy retrieval..."):
            try:
                st.session_state.golden_report = run_golden(top_k)
            except Exception as exc:
                st.error(f"Không chạy được golden dataset: {exc}")

    report = st.session_state.get("golden_report")
    if report:
        passed = sum(row["hit"] for row in report)
        st.metric("Context hit rate", f"{passed}/{len(report)} ({passed / len(report):.1%})")
        st.dataframe(report, use_container_width=True, hide_index=True)

with embedding_tab:
    st.subheader("Embedding và indexing")
    st.write("Đọc Markdown, chunk, embed và upsert vào vector store.")
    if st.button("▶ Run embedding", type="primary"):
        with st.spinner("Đang embedding và indexing..."):
            try:
                st.session_state.embedding_report = run_embedding()
            except Exception as exc:
                st.error(f"Embedding thất bại: {exc}")

    embedding_report = st.session_state.get("embedding_report")
    if embedding_report:
        st.success("Embedding hoàn tất.")
        columns = st.columns(5)
        columns[0].metric("Documents", embedding_report["documents"])
        columns[1].metric("Chunks", embedding_report["chunks"])
        columns[2].metric("Dimension", embedding_report["dimension"])
        columns[3].metric("Provider", embedding_report["provider"])
        columns[4].metric("Model", embedding_report["model"])
        st.code(f"Collection: {embedding_report['collection']}")
