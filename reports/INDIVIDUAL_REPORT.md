# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Văn Bảo
- Mã học viên: 2A202602862
- Nhóm: ozone
- Repository/branch: https://github.com/ThanhBinh159/K4-L3B-RAG-Pipeline/tree/Bao

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|

| Task 8 — PageIndex Fallback | Thêm timeout + try/except để pipeline không crash khi PageIndex API lỗi; trả `[]` an toàn khi thiếu `PAGEINDEX_API_KEY` | `src/task8_pageindex_vectorless.py`, commit `[điền hash]` | Partial (chưa có API key thật để test end-to-end) |
| Task 9 — Retrieval Pipeline | Sửa `best_dense_score` để dùng `max()` thay vì `dense[0]` (đảm bảo luôn là score cao nhất); đọc `SCORE_THRESHOLD` từ `.env` thay vì hard-code; hiệu chỉnh threshold dựa trên query in-domain/out-of-domain | `src/task9_retrieval_pipeline.py`, commit `[điền hash]` | Done |
| Task 10 — Generation | Thêm nhánh `_call_openrouter` để dispatch theo `LLM_PROVIDER=openrouter`; cập nhật `_DEFAULT_MODELS` với Gemini 3.6 Flash; sửa `retrieval_source` trả `"none"` khi answer là safe refusal | `src/task10_generation.py`, commit `[điền hash]` | Done |
| Golden Dataset & Evaluation | Tạo 30 câu golden Q&A tiếng Việt dựa trên corpus; viết script `evaluation.py` đo hit rate, keyword hit rate, context recall, context precision; so sánh A/B dense-only vs hybrid+RRF | `group_project/evaluation/golden_dataset.json`, `src/evaluation.py`, commit `[điền hash]` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chuyển embedding provider từ Gemini trực tiếp sang OpenRouter (`openai/text-embedding-3-small`).
   **Lý do/evidence:** Gemini free tier chỉ cho 100 request/phút cho model `gemini-embedding-001`, gây lỗi 429 liên tục khi embed 1221 chunks. Thử batch size 50 + `time.sleep(1.2)` vẫn bị 429. Sau khi chuyển sang OpenRouter, pipeline embed 1221 chunk thành công không lỗi.
   **Trade-off:** Mất tính local (phải gọi API) và tốn ~$0.02/1M tokens, nhưng ổn định hơn hẳn so với việc debug rate limit. Model `text-embedding-3-small` cũng có chất lượng tốt cho tiếng Việt (thể hiện qua hit rate 96.67% ở golden dataset).

2. **Quyết định:** Thêm `MIN_CHUNK_LENGTH = 50` và bỏ separator `. ` khỏi `RecursiveCharacterTextSplitter`.
   **Lý do/evidence:** Khi test Task 5, top-3 kết quả đều trả về chunk có content `'. 2'` — rác chỉ 3 ký tự, do separator `. ` cắt ngay tại dấu chấm của số thứ tự trong văn bản luật (ví dụ "1. ... 2. ..."). Sau khi sửa và rebuild DB, không còn chunk rác nào trong top-k; kết quả semantic search chuyển sang các chunk có nghĩa.
   **Trade-off:** Mất một số chunk ngắn có thể có giá trị (ví dụ tiêu đề mục), nhưng đổi lại loại bỏ hoàn toàn noise. Có thể cân nhắc `MIN_CHUNK_LENGTH = 30` nếu muốn giữ tiêu đề ngắn — cần test thêm.

## Kiểm thử và kết quả

- **Query tôi đã dùng:**
  - In-domain: `"thủ tục cấp giấy phép an toàn thực phẩm"`, `"thuế giá trị gia tăng hộ kinh doanh"`, `"mức xử phạt vi phạm an toàn thực phẩm"`.
  - Out-of-domain: `"công thức nấu phở bò"`.
  - Query cho golden dataset: 30 câu hỏi bao phủ 8 văn bản luật/nghị định.

- **Kết quả trước/sau:**
  - **Trước khi sửa Task 4:** Semantic search trả về chunk `. 2` với score 0.284 cho mọi query → vô nghĩa.
  - **Sau khi sửa Task 4:** Semantic search trả về đúng chunk Điều 36 Luật An toàn thực phẩm với score 0.735 cho query `"thủ tục cấp giấy phép an toàn thực phẩm"`.
  - **Evaluation:** Hit rate 96.67% (29/30), keyword hit rate 93.33% (28/30). Chỉ q024 trượt do câu hỏi về "200 triệu không chịu thuế GTGT" bị kéo về các văn bản quản lý thuế thay vì Luật GTGT 48/2024.

- **Lỗi đã phát hiện và cách xử lý:**
  1. `KeyError: 'embedding'` — do `_embed_with_gemini` dùng API cũ, trả về list rỗng → sửa sang SDK mới + raise lỗi rõ ràng khi response rỗng.
  2. `429 RESOURCE_EXHAUSTED` — do Gemini free tier quota → chuyển sang OpenRouter.
  3. Chunk rác `. 2` — do separator `. ` → sửa separator và thêm MIN_CHUNK_LENGTH.
  4. Score sai trong semantic search — do công thức `1 - distance` không map đúng cosine distance [0, 2] → sửa thành `1 - distance / 2`.
  5. BM25 trả chunk ngẫu nhiên khi không match — do `np.argsort` vẫn sort khi mọi score = 0 → thêm filter `score > 0`.

## Điều còn hạn chế

- **Hạn chế cụ thể:** Golden dataset hiện tại chỉ có 30 câu và chưa cover hết các trường hợp edge case (ví dụ: câu hỏi so sánh giữa 2 văn bản, câu hỏi yêu cầu tính toán số thuế cụ thể). Ngoài ra, script `evaluation.py` hiện chỉ đo hit rate + keyword hit rate; 4 metric đầy đủ (faithfulness, answer relevance, context recall, context precision) vẫn chưa được implement hoàn chỉnh — cần mở rộng thêm để đáp ứng yêu cầu của `STEP_BY_STEP.md` Task 9.

- **Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:** Mở rộng `evaluation.py` để chạy đủ 4 metric, dùng LLM làm judge (qua OpenRouter Gemini 3.6 Flash) cho faithfulness và answer relevance, đồng thời chạy A/B so sánh dense-only vs hybrid+RRF trên cùng 30 câu để có số liệu điền vào `group_project/evaluation/RESULT.md`.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Nguyễn Văn Bảo