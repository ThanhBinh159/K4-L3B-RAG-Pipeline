# Golden dataset: chạy online

Đã chạy 15 câu hỏi với `top_k=5`; embedding `ollama` (`bge-m3:latest`), generation `gemini` (`gemini-3.1-flash-lite`). Gateway và API key lấy từ `.env`; kết quả không lưu key.

## Overall scores

| Metric (proxy) | Score |
| --- | ---: |
| faithfulness | 1.000 |
| answer_relevance | 0.622 |
| context_recall | 1.000 |
| context_precision | 0.893 |

Từ chối: 0/15. Thời gian tổng: 158.0 giây.

## Generation modes

- `model_quote`: 15 câu

`model_quote` là đoạn model chọn và được đối chiếu nguyên văn với source. `extractive_fallback` hoặc `provider_error_fallback` là câu trích xuất từ corpus khi model không tạo được trích dẫn kiểm chứng được.

## Worst performers

- Câu 10: Theo Điều 21, bên kinh doanh cần cung cấp những thông tin cơ bản nào về sản phẩm cho người tiêu dùng? — answer relevance 0.349, context recall 1, mode `model_quote`.
- Câu 5: Theo Điều 7 Luật Thuế thu nhập cá nhân 109/2025/QH15, cá nhân cư trú kinh doanh có doanh thu năm từ 500 triệu đồng trở xuống có phải nộp thuế TNCN không? — answer relevance 0.439, context recall 1, mode `model_quote`.
- Câu 4: Theo Điều 52, quy định tại Điều 13 về hộ kinh doanh có hiệu lực từ ngày nào? — answer relevance 0.500, context recall 1, mode `model_quote`.
- Câu 6: Điều 7 xác định thuế TNCN đối với thu nhập từ kinh doanh trên ngưỡng doanh thu bằng cách nào? — answer relevance 0.500, context recall 1, mode `model_quote`.
- Câu 13: Theo bài hướng dẫn, nộp hồ sơ đăng ký thành lập hộ kinh doanh ở đâu? — answer relevance 0.533, context recall 1, mode `model_quote`.

## Metric definitions and limits

- Faithfulness: phần trích trong câu trả lời xuất hiện ở source được dẫn; đây là kiểm tra văn bản, không phải đánh giá suy luận.
- Answer relevance: token F1 với đáp án tham chiếu.
- Context recall: có ít nhất một chunk đúng URL và đúng Điều nếu golden có nhãn Điều.
- Context precision: average precision@5 theo nhãn URL/Điều.
- Các metric là proxy offline tính trên câu trả lời và kết quả retrieval online; chưa phải RAGAS hoặc xác nhận hiệu lực pháp luật.
- Chi tiết từng câu nằm trong `online_results.json`; báo cáo A/B dense/hybrid riêng ở `RESULT.md`.

## Reproduce

```bash
python -m src.evaluate_online
```
