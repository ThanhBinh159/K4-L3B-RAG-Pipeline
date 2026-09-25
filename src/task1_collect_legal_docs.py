"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Chủ đề nhóm: Pháp luật cho hộ kinh doanh (đăng ký kinh doanh, thuế, hóa đơn,
thương mại điện tử).

Hướng dẫn:
    1. Điền URL PDF/DOCX công khai vào SOURCES bên dưới (tối thiểu 3 file).
    2. Nếu nguồn chặn crawler/robot hoặc yêu cầu đăng nhập (vd. tải từ Google
       Drive cá nhân), tải thủ công rồi đặt file trực tiếp vào
       data/landing/legal/ — chạy lại download_documents() vẫn an toàn vì nó
       chỉ ghi đè các file có trong SOURCES, không xoá file đã có sẵn.
    3. Đặt tên không dấu và thể hiện đúng nội dung.
"""

from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# TODO (nhóm điền): thay bằng URL PDF/DOCX công khai thật, ví dụ từ
# thuvienphapluat.vn, vanban.chinhphu.vn, gdt.gov.vn...
# Key = tên file lưu trong data/landing/legal/, value = URL tải trực tiếp.
SOURCES: dict[str, str] = {
    "Luật An toàn thực phẩm 55/2010/QH12": "https://congbao.chinhphu.vn/van-ban/luat-so-55-2010-qh12-562/1214.htm",
    "Luật Hỗ trợ doanh nghiệp nhỏ và vừa 04/2017/QH14": "https://congbao.chinhphu.vn/van-ban/luat-so-04-2017-qh14-24225/18418.htm",
    "Luật Quản lý thuế 108/2025/QH15": "https://congbao.chinhphu.vn/van-ban/luat-so-108-2025-qh15-468670/61635.htm",
    "Luật Thuế giá trị gia tăng 48/2024/QH15": "https://congbao.chinhphu.vn/van-ban/luat-so-48-2024-qh15-43576.htm",
    "Luật Thuế thu nhập cá nhân 109/2025/QH15": "https://congbao.chinhphu.vn/van-ban/luat-so-109-2025-qh15-468671/61623.htm",
}

REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (K4-L3B-RAG-Pipeline data collector)"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải PDF/DOCX từ SOURCES vào data/landing/legal/.

    Bỏ qua các URL rỗng và các lỗi tải riêng lẻ (không dừng cả batch) để một
    nguồn lỗi không chặn các nguồn còn lại. In cảnh báo nếu sau khi chạy vẫn
    chưa đủ 3 tài liệu hợp lệ (ai đó có thể đã copy tay vào thư mục).
    """
    setup_directory()

    if not SOURCES:
        print(
            "SOURCES đang rỗng. Điền URL vào SOURCES, hoặc copy thủ công "
            f"file PDF/DOCX vào {DATA_DIR} rồi chạy lại."
        )

    headers = {"User-Agent": USER_AGENT}
    for filename, url in SOURCES.items():
        if not url:
            print(f"Skip {filename}: URL rỗng")
            continue
        destination = DATA_DIR / filename
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            destination.write_bytes(response.content)
            print(f"Saved: {destination} ({len(response.content)} bytes)")
        except requests.RequestException as error:
            print(f"Failed: {filename} <- {url} ({error})")

    existing = [
        path
        for path in DATA_DIR.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    ]
    if len(existing) < 3:
        print(
            f"Cảnh báo: mới có {len(existing)} tài liệu hợp lệ trong "
            f"{DATA_DIR}, cần tối thiểu 3."
        )
    else:
        print(f"OK: {len(existing)} tài liệu hợp lệ trong {DATA_DIR}.")


if __name__ == "__main__":
    setup_directory()
    download_documents()
