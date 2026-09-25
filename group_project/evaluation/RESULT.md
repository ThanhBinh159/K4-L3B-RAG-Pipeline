# Evaluation: pháp luật hộ kinh doanh

Đánh giá trên 15 câu hỏi trong `golden_dataset.json`; cùng corpus, top_k=5 và cùng bộ trích xuất câu trả lời offline. Embedding gọi OpenRouter bằng API key trong `.env`. Tắt PageIndex ở cả hai nhánh để so sánh retrieval.

## Overall scores

| Metric (offline proxy) | Dense only | Hybrid + RRF | Δ |
| --- | ---: | ---: | ---: |
| faithfulness | 1.000 | 1.000 | +0.000 |
| answer_relevance | 0.550 | 0.550 | +0.000 |
| context_recall | 1.000 | 1.000 | +0.000 |
| context_precision | 0.901 | 0.910 | +0.010 |

## A/B comparison

Dense dùng cosine trên Chroma; hybrid gộp thứ hạng dense và BM25Plus bằng RRF (k=60). Cả hai dùng embedding `openrouter` (`nvidia/llama-nemotron-embed-vl-1b-v2:free`), cùng 15 câu, không gọi LLM và không gọi PageIndex.

**Định nghĩa proxy:** faithfulness = đoạn trích trong câu trả lời xuất hiện nguyên văn ở source được dẫn; answer relevance = token F1 giữa câu trả lời và đáp án tham chiếu; context recall = có ít nhất một chunk đúng URL và đúng Điều (nếu có); context precision = average precision@5 trên các chunk có nhãn URL/Điều đúng. Các số này không phải điểm RAGAS/LLM judge hay xác nhận pháp lý.

## Worst performers

- Câu 8: Theo Điều 12, thuế GTGT theo phương pháp trực tiếp trên doanh thu được tính thế nào? — context recall 1, answer relevance 0.262.
- Câu 10: Theo Điều 21, bên kinh doanh cần cung cấp những thông tin cơ bản nào về sản phẩm cho người tiêu dùng? — context recall 1, answer relevance 0.303.
- Câu 13: Theo bài hướng dẫn, nộp hồ sơ đăng ký thành lập hộ kinh doanh ở đâu? — context recall 1, answer relevance 0.392.
- Câu 5: Theo Điều 7 Luật Thuế thu nhập cá nhân 109/2025/QH15, cá nhân cư trú kinh doanh có doanh thu năm từ 500 triệu đồng trở xuống có phải nộp thuế TNCN không? — context recall 1, answer relevance 0.439.
- Câu 4: Theo Điều 52, quy định tại Điều 13 về hộ kinh doanh có hiệu lực từ ngày nào? — context recall 1, answer relevance 0.500.

## Recommendations

- Mở rộng corpus theo từng điều và xác minh hiệu lực, sửa đổi văn bản trước khi dùng để tư vấn thực tế.
- Thử bộ reranker và mở rộng câu hỏi golden; đo lại trên cùng tập để kiểm tra mức cải thiện.
- Đánh giá thủ công tính đúng pháp lý và citation; phép đo lexical không phát hiện suy luận sai hoặc thay đổi hiệu lực.
- Cấu hình API key riêng để kiểm thử PageIndex và các LLM provider; nhánh cloud chưa được đo trong báo cáo này.

## Reproduce

```bash
python -m src.task4_chunking_indexing
python -m src.evaluate
```
