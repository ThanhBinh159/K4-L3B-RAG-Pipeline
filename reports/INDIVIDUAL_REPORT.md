# Báo cáo đóng góp cá nhân — nhóm 3 thành viên

Điền họ tên và mã học viên sau. Mỗi thành viên hoàn thiện phần riêng dưới đây. Phạm vi phân công là gợi ý theo các mảng của dự án; sửa cho đúng việc thực tế đã làm. Chỉ ghi nhận đóng góp có thể đối chiếu bằng file, commit, test, pull request hoặc kết quả evaluation.

## Thành viên 1 — Dữ liệu và corpus

### Thông tin

- Họ và tên:
- Mã học viên:
- Nhóm:
- Branch/commit liên quan:

### Phần việc

| Hạng mục gợi ý | Việc tôi trực tiếp làm | Bằng chứng (file/commit/test) | Trạng thái |
| --- | --- | --- | --- |
| Chọn lọc luật và điều khoản liên quan đến hộ kinh doanh | | `src/prepare_household_business_corpus.py`, `data/standardized/legal/` | |
| Thu thập PDF Công báo và bài hướng dẫn chính thức | | `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py`, `data/landing/` | |
| Chuẩn hóa tài liệu và giữ metadata/URL nguồn | | `src/task3_convert_markdown.py`, `data/standardized/` | |
| Mô tả phạm vi, nguồn và giới hạn dữ liệu | | `docs/HKD_CORPUS.md` | |

### Kiểm tra, quyết định và hạn chế

- Test hoặc kiểm tra dữ liệu đã chạy:
- Kết quả và lỗi dữ liệu đã xử lý:
- Quyết định kỹ thuật tôi tham gia, lý do và đánh đổi:
- Hạn chế cụ thể và việc cần làm tiếp:

### Xác nhận

Tôi xác nhận phần khai báo phản ánh đúng đóng góp của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Họ tên:

---

## Thành viên 2 — Indexing và retrieval

### Thông tin

- Họ và tên:
- Mã học viên:
- Nhóm:
- Branch/commit liên quan:

### Phần việc

| Hạng mục gợi ý | Việc tôi trực tiếp làm | Bằng chứng (file/commit/test) | Trạng thái |
| --- | --- | --- | --- |
| Chunking, embedding và lưu vector trong Chroma | | `src/task4_chunking_indexing.py` | |
| Dense search và BM25 trên cùng corpus | | `src/task5_semantic_search.py`, `src/task6_lexical_search.py` | |
| RRF, lọc kết quả và gộp các chunk cùng nguồn | | `src/task7_reranking.py`, `src/task9_retrieval_pipeline.py` | |
| Fallback PageIndex và xử lý lỗi retrieval | | `src/task8_pageindex_vectorless.py`, `src/task9_retrieval_pipeline.py` | |

### Kiểm tra, quyết định và hạn chế

- Test hoặc query đã chạy:
- Kết quả trước/sau và lỗi xếp hạng đã xử lý:
- Quyết định kỹ thuật tôi tham gia, lý do và đánh đổi:
- Hạn chế cụ thể và việc cần làm tiếp:

### Xác nhận

Tôi xác nhận phần khai báo phản ánh đúng đóng góp của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Họ tên:

---

## Thành viên 3 — Generation, giao diện và đánh giá

### Thông tin

- Họ và tên:
- Mã học viên:
- Nhóm:
- Branch/commit liên quan:

### Phần việc

| Hạng mục gợi ý | Việc tôi trực tiếp làm | Bằng chứng (file/commit/test) | Trạng thái |
| --- | --- | --- | --- |
| Generation có citation kiểm chứng được và safe refusal | | `src/task10_generation.py` | |
| Chatbot Streamlit và hiển thị nguồn | | `app.py` | |
| Golden dataset và đánh giá A/B offline | | `group_project/evaluation/golden_dataset.json`, `src/evaluate.py`, `group_project/evaluation/RESULT.md` | |
| Đánh giá online và báo cáo metric proxy | | `src/evaluate_online.py`, `group_project/evaluation/RESULT_ONLINE.md` | |
| Hướng dẫn chạy và tài liệu dự án | | `README.md`, `docs/` | |

### Kiểm tra, quyết định và hạn chế

- Test, query hoặc demo đã chạy:
- Kết quả và lỗi generation/citation/UI đã xử lý:
- Quyết định kỹ thuật tôi tham gia, lý do và đánh đổi:
- Hạn chế cụ thể và việc cần làm tiếp:

### Xác nhận

Tôi xác nhận phần khai báo phản ánh đúng đóng góp của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Họ tên:
