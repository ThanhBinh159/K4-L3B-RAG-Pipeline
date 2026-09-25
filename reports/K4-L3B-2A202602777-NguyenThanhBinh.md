# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Thanh Bình
- Mã học viên: 2A202602777
- Nhóm: ozon
- Repository/branch: `https://github.com/ThanhBinh159/K4-L3B-RAG-Pipeline.git`

## Phần việc đã thực hiện

| Module/deliverable | Việc đã thực hiện | File chính | Trạng thái |
|---|---|---|---|
| Task 4 — Chunking, embedding và indexing | Đọc Markdown chuẩn hoá, chia chunk có overlap, tạo embedding local ổn định, lưu vào vector store; hỗ trợ cấu hình provider/model | `src/task4_chunking_indexing.py` | Done |
| Task 5 — Semantic search | Dùng chung `embed_texts()` với Task 4, tìm kiếm theo cosine similarity và trả kết quả theo `SearchResult` | `src/task5_semantic_search.py` | Done |
| Task 6 — Lexical search | Xây dựng BM25 trên cùng corpus chunks, tìm kiếm từ khoá và chuẩn hoá kết quả | `src/task6_lexical_search.py` | Done |
| Task 7 — RRF reranking | Hợp nhất các danh sách dense/BM25 theo Reciprocal Rank Fusion, không cộng trực tiếp các thang điểm khác nhau | `src/task7_reranking.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Dùng chung embedding giữa indexing và semantic search.**
   **Lý do/evidence:** Task 4 và Task 5 cùng gọi `embed_texts()`, giữ cùng dimension và collection name; contract test xác nhận query dùng đúng embedding chung.
   **Trade-off:** Embedding local hash chạy ổn định/offline nhưng chất lượng ngữ nghĩa thấp hơn embedding model chuyên dụng.

2. **Dùng RRF để hợp nhất dense và BM25.**
   **Lý do/evidence:** Task 7 cộng điểm theo thứ hạng với `k=60`, giữ item theo ID và trả về tối đa `top_k`; contract test kiểm tra thứ tự và không mutate input.
   **Trade-off:** RRF không tận dụng trực tiếp độ lớn cosine/BM25, nhưng tránh trộn hai thang điểm không tương thích.

## Kiểm thử và kết quả

- Chạy `\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q`: **15 passed**.
- Chạy `\.venv\Scripts\python.exe -m pytest -q`: **20 passed**.
- Chạy embedding/indexing trên corpus local: **1057 chunks** được index.
- Kiểm tra golden retrieval sau khi chuẩn hoá phần mở rộng nguồn: **15/15 context hits**.

## Điều còn hạn chế

- Embedding hiện dùng vector hash local để pipeline chạy được không cần API key; chưa đánh giá định lượng với embedding model hosted.
- Chưa thực hiện đánh giá live faithfulness/answer relevance bằng model DeepSeek vì chưa có `DEEPSEEK_API_KEY` hợp lệ trong môi trường chạy.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh phần việc có thể kiểm tra lại bằng source code, test và kết quả pipeline.

- Ngày: 2026-09-25
- Tên thành viên: Nguyễn Thanh Bình
