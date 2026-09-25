"""Download original law PDFs from the official Công báo pages."""

from __future__ import annotations

from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "landing" / "legal"
LEGAL_SOURCES = {
    "quan_ly_thue_108_2025.pdf": "https://congbao.chinhphu.vn/van-ban/luat-so-108-2025-qh15-468670/61635.htm",
    "thue_thu_nhap_ca_nhan_109_2025.pdf": "https://congbao.chinhphu.vn/van-ban/luat-so-109-2025-qh15-468671/61623.htm",
    "thue_gia_tri_gia_tang_48_2024.pdf": "https://congbao.chinhphu.vn/van-ban/luat-so-48-2024-qh15-43576.htm",
    "ho_tro_doanh_nghiep_nho_va_vua_04_2017.pdf": "https://congbao.chinhphu.vn/van-ban/luat-so-04-2017-qh14-24225/18418.htm",
    "an_toan_thuc_pham_55_2010.pdf": "https://congbao.chinhphu.vn/van-ban/luat-so-55-2010-qh12-562/1214.htm",
}


def find_pdf_url(html: str, page_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=True):
        href = unescape(link["href"])
        if ".pdf" in href.lower():
            return urljoin(page_url, href)
    raise ValueError(f"No PDF link on {page_url}")


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_documents() -> None:
    setup_directory()
    for filename, page_url in LEGAL_SOURCES.items():
        output = DATA_DIR / filename
        if output.exists() and output.read_bytes()[:4] == b"%PDF":
            print(f"Reused: {output}")
            continue
        page = requests.get(page_url, timeout=30)
        page.raise_for_status()
        pdf_url = find_pdf_url(page.text, page_url)
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        if response.content[:4] != b"%PDF":
            raise ValueError(f"Invalid PDF from {pdf_url}")
        output.write_bytes(response.content)
        print(f"Saved: {output}")


if __name__ == "__main__":
    download_documents()
