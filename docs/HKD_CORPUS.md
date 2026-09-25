# Corpus RAG: pháp luật cho hộ kinh doanh

## Mục tiêu và phạm vi

Tập dữ liệu này phục vụ câu hỏi về thuế, hóa đơn, chuyển đổi hộ kinh doanh thành doanh nghiệp, giao dịch với người tiêu dùng và an toàn thực phẩm (khi kinh doanh thực phẩm). Đây là corpus thí nghiệm cho bài RAG, không phải tập văn bản pháp luật đầy đủ.

## Nguồn và cách lọc

- Corpus gốc: [Vietnam laws IR](https://huggingface.co/datasets/justicedao/ipfs_vietnam_laws_ir), revision `89013dcc37dea35d0d858b2f07517bf425f76729`. Chỉ tải 11 shard `data/corpus` (khoảng 12,6 MB) vào `.cache/`; không dùng chỉ mục BM25/vector dựng sẵn.
- Bộ lọc được ghi trong `src/prepare_household_business_corpus.py`: chọn số điều theo từng luật, bỏ bản ghi tách điều lỗi (tiêu đề hoặc thân bài không bắt đầu bằng `Điều N.`), và bỏ URL trùng. Kết quả: 6 tệp Markdown, 54 điều, có `entry_cid`, URL nguồn và ngày bản chụp. Manifest: `data/standardized/legal/hkd_manifest.json`.
- 5 PDF gốc từ Công báo ở `data/landing/legal/` để đối chiếu. Các điều Markdown được xuất trực tiếp từ dataset, không phải OCR lại PDF.
- 6 bài hướng dẫn từ [Cổng Thông tin Chính phủ](https://xaydungchinhsach.chinhphu.vn/) ở `data/landing/news/` (JSON) và `data/standardized/news/` (Markdown). Mỗi bài có URL, tiêu đề, ngày thu thập. Đây là nguồn giải thích; khi nội dung khác văn bản quy phạm, ưu tiên văn bản chính thức đang có hiệu lực.

## Sáu nhóm văn bản luật

| Chủ đề | Văn bản | Nguồn |
| --- | --- | --- |
| Quản lý thuế, mã số thuế, hóa đơn | Luật Quản lý thuế 108/2025/QH15 | [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-108-2025-qh15-468670/61635.htm) |
| Thuế thu nhập từ kinh doanh | Luật Thuế thu nhập cá nhân 109/2025/QH15 | [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-109-2025-qh15-468671/61623.htm) |
| Thuế giá trị gia tăng | Luật Thuế giá trị gia tăng 48/2024/QH15 | [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-48-2024-qh15-43576.htm) |
| Chuyển đổi lên doanh nghiệp | Luật Hỗ trợ doanh nghiệp nhỏ và vừa 04/2017/QH14 | [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-04-2017-qh14-24225/18418.htm) |
| Bán hàng cho người tiêu dùng | Luật Bảo vệ quyền lợi người tiêu dùng 19/2023/QH15 | [VBPL](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=161263) |
| Kinh doanh thực phẩm | Luật An toàn thực phẩm 55/2010/QH12 | [Công báo](https://congbao.chinhphu.vn/van-ban/luat-so-55-2010-qh12-562/1214.htm) |

## Dùng trong pipeline

Chạy `python -m src.prepare_household_business_corpus --download` để tải lại phần corpus và xuất Markdown. `load_documents()` đọc Markdown trong `data/standardized/`, tạo `Document` theo contract và giữ `url`. `chunk_documents()` chia theo ranh giới điều luật trước khi tách thành chunk nhỏ, gắn thêm `article` trong metadata.

## Giới hạn dữ liệu

- Dataset chỉ bao gồm luật/hiến pháp; thủ tục đăng ký hộ kinh doanh và nhiều chi tiết thuế nằm ở nghị định, thông tư. Sáu bài hướng dẫn giúp đặt câu hỏi thí nghiệm nhưng không thay thế toàn văn văn bản quy phạm.
- Dataset gắn nhãn giấy phép `other`; giữ URL và thông tin nguồn khi tái sử dụng, đồng thời kiểm tra điều kiện sử dụng trên trang dữ liệu và trang văn bản gốc trước khi công bố lại corpus.
- Trường `law_status` của dataset không được dùng để kết luận hiệu lực: corpus có cả văn bản cũ được gắn `current`. Cần kiểm tra từng văn bản tại Công báo/VBPL trước khi khẳng định quy định hiện hành.
- Bản tách điều tự động của nguồn có thể lệch ranh giới. Bộ lọc bỏ các trường hợp tiêu đề/thân bài sai rõ ràng; vẫn cần rà soát thủ công các đoạn dùng trong golden dataset và các câu trả lời pháp lý.
- `group_project/evaluation/golden_dataset.json` có 15 câu hỏi với đáp án và đoạn bằng chứng từ corpus. Chưa có kết quả 4 metric hoặc báo cáo A/B; không coi golden dataset là kết quả đánh giá RAG.
