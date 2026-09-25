"""Streamlit chat for the household-business legal RAG corpus."""

import streamlit as st

from src.task10_generation import generate_with_citation


st.set_page_config(page_title="Pháp luật hộ kinh doanh", page_icon="📚", layout="wide")


def show_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Nguồn tham khảo ({len(sources)})"):
        for index, item in enumerate(sources, 1):
            metadata = item["metadata"]
            title = metadata["title"]
            url = metadata.get("url")
            st.markdown(f"**[{index}] {title}**" + (f" · [Văn bản gốc]({url})" if url else ""))
            st.caption(f"{metadata['source']} · {item['retrieval_method']} · điểm {item['score']:.3f}" +
                       (f" · {metadata['article']}" if metadata.get("article") else ""))
            st.write(item["content"][:600])


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("Pháp luật hộ kinh doanh")
    st.caption("Tra cứu trong corpus luật và bài hướng dẫn đã chọn. Kiểm tra văn bản gốc trước khi áp dụng.")
    top_k = st.slider("Số đoạn tham khảo", 3, 10, 5)

st.title("Hỏi đáp pháp luật hộ kinh doanh")
st.caption("Ví dụ: Mã số thuế của hộ kinh doanh là gì?")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            show_sources(message.get("sources", []))

query = st.chat_input("Nhập câu hỏi về hộ kinh doanh...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Đang tra cứu..."):
            result = generate_with_citation(query, top_k=top_k)
        st.markdown(result["answer"])
        show_sources(result["sources"])
    st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result["sources"]})
