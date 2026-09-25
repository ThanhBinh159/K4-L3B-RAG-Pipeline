# Báo cáo đánh giá

Báo cáo số liệu chính thức được duy trì cùng golden dataset trong `group_project/evaluation/`:

- [Kết quả A/B offline](../group_project/evaluation/RESULT.md): dense-only so với hybrid + RRF, dùng cùng 15 câu hỏi và câu trả lời trích xuất.
- [Kết quả chạy online](../group_project/evaluation/RESULT_ONLINE.md): Ollama `bge-m3:latest` và Gemini gateway trên 15 câu hỏi.

Cả hai báo cáo dùng metric proxy được mô tả trong từng file. Không diễn giải điểm số thành xác nhận pháp lý hoặc đánh giá bởi chuyên gia. Chạy lại bằng `python -m src.evaluate` hoặc `python -m src.evaluate_online` theo cấu hình cần đo.
