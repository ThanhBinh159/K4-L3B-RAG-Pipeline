# Day 8 — RAG Pipeline

## Đề tài nhóm: pháp luật cho hộ kinh doanh

Corpus hiện có 6 luật (54 điều được chọn) từ [Vietnam laws IR](https://huggingface.co/datasets/justicedao/ipfs_vietnam_laws_ir), 5 PDF gốc từ Công báo và 6 bài hướng dẫn từ Cổng Thông tin Chính phủ. Dữ liệu đã chuẩn hóa nằm trong `data/standardized/legal/` và `data/standardized/news/`; `src.task4_chunking_indexing.load_documents()` đọc được cả hai loại và giữ URL nguồn để trích dẫn.

Tái tạo phần văn bản luật đã lọc từ revision cố định của dataset:

```bash
python -m src.prepare_household_business_corpus --download
```

Xem [phạm vi và nguồn dữ liệu](docs/HKD_CORPUS.md) trước khi xây golden dataset. Các điều trong corpus là bản chụp phục vụ nghiên cứu; cần đối chiếu hiệu lực và văn bản hướng dẫn mới tại nguồn chính thức trước khi đưa ra kết luận pháp lý.

## Mục tiêu

Mỗi nhóm xây dựng một chatbot RAG trả lời câu hỏi từ bộ tài liệu do nhóm thu thập. Sản phẩm phải có hybrid retrieval, citation, giao diện chat và báo cáo đánh giá.

Nhóm tự chọn bài toán và thu thập dữ liệu phù hợp; repo không cung cấp dữ liệu mẫu.

## Sản phẩm phải nộp

- Repository nhóm chạy được.
- Tối thiểu 3 tài liệu chính sách và 5 bài viết/page do nhóm tự thu thập.
- Pipeline: convert → chunk → index → dense + BM25 → RRF → fallback → generation có citation.
- Chatbot Streamlit hiển thị câu trả lời và nguồn đã dùng.
- Golden dataset tối thiểu 15 câu; đánh giá 4 metric và so sánh A/B.
- `group_project/evaluation/RESULT.md`.
- Mỗi thành viên nộp báo cáo cá nhân theo template trong `group_project/ịndividual/INDIVIDUAL_REPORT.md`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

Điền API key cần dùng trong `.env`; không commit file này.

Mẫu `.env.example` dùng embedding Ollama `bge-m3:latest` và generation trích xuất. Khởi động Ollama, tải model và tạo chỉ mục:

```bash
ollama pull bge-m3
ollama serve
python -m src.task4_chunking_indexing
```

Trên Windows, nếu `ollama` chưa có trong PATH, dùng `& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve`. Nếu ứng dụng Ollama đã chạy thì không cần mở thêm server. `bge-m3` được gọi qua `/api/embed` ở `OLLAMA_BASE_URL`. Sau khi đổi embedding provider hoặc model, chạy lại lệnh index; mỗi cấu hình dùng một collection Chroma riêng. Có thể dùng `EMBEDDING_PROVIDER=local_lsa` để chạy hoàn toàn offline mà không cần Ollama, hoặc `EMBEDDING_PROVIDER=openrouter` với `EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free` và `OPENROUTER_API_KEY`.

Để sinh câu trả lời qua gateway tương thích Gemini, cấu hình thêm trong `.env`:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.1-flash-lite
GEMINI_BASE_URL=http://localhost:8317
GEMINI_API_KEY=your_gateway_key_here
```

Ứng dụng gọi Gemini SDK qua `GEMINI_BASE_URL`, sau đó chỉ giữ phần trích nguyên văn khớp với source được dẫn; nếu model không đáp ứng, ứng dụng dùng câu trả lời trích xuất từ corpus. Gateway và model phải đang hoạt động ở địa chỉ đã cấu hình.

```bash
# 1. Thu thập và chuẩn hoá
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Index và kiểm tra contract
python -m src.task4_chunking_indexing
pytest -q

# 3. Chạy sản phẩm
streamlit run app.py
```

Đánh giá A/B trên 15 câu hỏi và ghi `group_project/evaluation/RESULT.md`:

```bash
python -m src.evaluate
```

`RESULT.md` là phép so sánh A/B trước đó với embedding OpenRouter và câu trả lời trích xuất offline. Để chạy toàn bộ golden dataset với Ollama và provider generation đang cấu hình trong `.env`:

```bash
python -m src.evaluate_online
```

Lệnh ghi checkpoint từng câu vào `group_project/evaluation/online_results.json` và tổng hợp ở `group_project/evaluation/RESULT_ONLINE.md`. Bốn metric đều là proxy so khớp văn bản/nhãn nguồn, chưa phải RAGAS hoặc đánh giá pháp lý bởi chuyên gia. PageIndex là fallback tùy chọn khi điền `PAGEINDEX_API_KEY` và upload PDF.

## Lộ trình 3 giờ

| Mốc                  | Thời gian | Kết quả cần có                           |
| -------------------- | --------: | ---------------------------------------- |
| 0. Setup             |   10 phút | Môi trường và `.env` sẵn sàng            |
| 1. Data              |   25 phút | ≥3 legal, ≥5 news, Markdown đã chuẩn hoá |
| 2. Index & search    |   30 phút | ChromaDB, dense search và BM25 chạy được |
| 3. Fusion & fallback |   25 phút | RRF và fallback tuân thủ contract        |
| 4. Generation & UI   |   30 phút | Chatbot trả lời có citation              |
| 5. Evaluation        |   30 phút | 15+ Q&A, 4 metric, A/B comparison        |
| 6. Demo & handoff    |   30 phút | Test, report, demo và push repository    |

## Lưu ý quy tắc để có code quality tốt:

- Dense và BM25 nên cùng trả về `SearchResult` theo một schema.
- RRF chỉ nên dùng để gộp thứ hạng và chỉ chạy một lần.
- Fallback dùng cosine score gốc của dense retrieval.
- Threshold phải được hiệu chỉnh trên query in domain và out of domain, không có một con số đúng cho mọi corpus.

## Tài liệu

- [Module contracts](docs/MODULE_CONTRACTS.md): schema, interface và invariant mà code/test nên tuân theo.
- [Step-by-step guide](docs/STEP_BY_STEP.md): thứ tự triển khai và tiêu chí hoàn thành từng bước.
- [Grading rubric](docs/GRADING_RUBRIC.md): Rubric thang điểm.
- [Individual report](group_project/ịndividual/INDIVIDUAL_REPORT.md): template báo cáo cá nhân.
- [Suggested topics](docs/SUGGESTED_TOPICS.md): danh sách chủ đề tham khảo, không bắt buộc.

## Kiểm tra

```bash
# Contract tests
pytest tests/test_contracts.py -q

# Acceptance tests
pytest tests/test_acceptance.py -q

# Toàn bộ
pytest -q
```
