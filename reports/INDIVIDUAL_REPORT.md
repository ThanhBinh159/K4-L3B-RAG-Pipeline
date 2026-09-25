# Báo cáo đóng góp cá nhân

> **Bản tham khảo:** nội dung mẫu dưới đây được tổng hợp từ repo. Hãy giữ họ tên/mã học viên đã điền và chỉnh phần mô tả để phản ánh đúng công việc bạn trực tiếp thực hiện.

## Thông tin

- Họ và tên: Phạm Văn Kiên
- Mã học viên: 2A202602590
- Nhóm:
- Repository/branch:
- Commit liên quan:

## Phạm vi công việc: Task 1, Task 2, Task 3

| Task | Nội dung công việc mẫu | Bằng chứng trong repo |
| --- | --- | --- |
| Task 1 — Thu thập tài liệu pháp luật | Thu thập và chọn tài liệu pháp luật liên quan đến hộ kinh doanh; lưu thông tin nguồn để có thể truy vết. | `src/task1_collect_legal_docs.py`, `data/landing/` |
| Task 2 — Crawl bài hướng dẫn | Lấy bài hướng dẫn liên quan từ nguồn đã chọn, giữ URL và metadata để phân biệt với văn bản quy phạm. | `src/task2_crawl_news.py`, `data/landing/` |
| Task 3 — Chuyển đổi Markdown | Chuẩn hóa tài liệu thu thập thành Markdown để các bước sau có thể xử lý; kiểm tra đầu ra và metadata. | `src/task3_convert_markdown.py`, `data/standardized/`, `docs/HKD_CORPUS.md` |

## Test hoặc kiểm tra dữ liệu đã chạy

- Chạy các lệnh thu thập và chuyển đổi theo hướng dẫn trong README:
  - `python -m src.task1_collect_legal_docs`
  - `python -m src.task2_crawl_news`
  - `python -m src.task3_convert_markdown`
- Kiểm tra corpus sau lọc được ghi nhận trong tài liệu dự án: **6 luật, 54 điều**, **5 PDF Công báo** và **6 bài hướng dẫn**.
- Kiểm tra đầu ra Markdown có nội dung tài liệu và URL nguồn; đối chiếu các thư mục `data/landing/`, `data/standardized/` cùng `docs/HKD_CORPUS.md`.

## Kết quả và lỗi dữ liệu đã xử lý

- Tập dữ liệu được giới hạn vào nội dung phục vụ đề tài pháp luật hộ kinh doanh; giữ lại URL nguồn để truy nguyên tài liệu.
- Loại các bản ghi tách điều không hợp lệ và nguồn trùng trong bước chuẩn bị corpus; chuẩn hóa đầu ra Markdown để dùng nhất quán ở các bước tiếp theo.
- Phân biệt văn bản pháp luật với bài hướng dẫn, tránh xem bài viết phổ biến chính sách như căn cứ quy phạm độc lập.

## Quyết định kỹ thuật tôi tham gia, lý do và đánh đổi

- Ưu tiên nguồn pháp luật và nguồn hướng dẫn có xuất xứ, đồng thời lưu URL trong dữ liệu. Cách này giúp kiểm tra lại nguồn; việc phụ thuộc khả năng truy cập website có thể làm bước thu thập cần chạy lại khi trang thay đổi.
- Lưu tài liệu đã thu thập trước khi chuyển đổi, rồi xuất bản chuẩn hóa sang Markdown. Cách này giữ được đầu vào để đối chiếu khi lỗi chuyển đổi; đổi lại cần quản lý cả dữ liệu gốc lẫn dữ liệu chuẩn hóa.
- Giới hạn corpus vào phạm vi hộ kinh doanh để tăng độ liên quan cho bài toán. Đánh đổi là corpus chưa bao quát toàn bộ quy định có thể liên quan đến một tình huống pháp lý cụ thể.

## Hạn chế cụ thể và việc cần làm tiếp

- Kiểm tra hiệu lực và phiên bản mới nhất của từng văn bản, bổ sung ngày ban hành/ngày hiệu lực và quan hệ sửa đổi nếu metadata nguồn chưa đủ.
- Mở rộng corpus từ nguồn quy phạm chính thức có liên quan, đồng thời tiếp tục lọc bài hướng dẫn để tránh nội dung cũ hoặc không sát đề tài.
- Bổ sung kiểm tra tự động cho URL thiếu, tài liệu trùng, lỗi chuyển đổi và tính ổn định khi chạy lại các Task 1–3.

## Xác nhận đóng góp

Tôi xác nhận nội dung sau khi chỉnh sửa phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Họ tên:
