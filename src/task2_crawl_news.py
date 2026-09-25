"""
Task 2 — Crawl bài viết/thông báo.

Chủ đề nhóm: Pháp luật cho hộ kinh doanh.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI (fallback: requests + trích xuất thô nếu
       Crawl4AI/Playwright chưa cài được trong môi trường của bạn).
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy (nếu dùng Crawl4AI):
    python -m playwright install chromium
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# TODO (nhóm điền): thay bằng >= 5 URL bài viết công khai thật về
# hộ kinh doanh (đăng ký kinh doanh, thuế khoán, hóa đơn điện tử...).
ARTICLE_URLS: list[str] = [
    "https://xaydungchinhsach.chinhphu.vn/bieu-mau-dang-ky-ho-kinh-doanh-11926091009173649.htm",
    "https://xaydungchinhsach.chinhphu.vn/quy-dinh-ho-so-trinh-tu-thu-tuc-dang-ky-thanh-lap-ho-kinh-doanh-119250702172916754.htm",
    "https://xaydungchinhsach.chinhphu.vn/truong-hop-duoc-giam-thue-gtgt-ho-kinh-doanh-lap-hoa-don-ke-khai-thue-nhu-the-nao-119260423055529827.htm",
    "https://xaydungchinhsach.chinhphu.vn/toan-van-thong-tu-152-2025-tt-bt-huong-dan-ke-toan-cho-cac-ho-kinh-doanh-ca-nhan-kinh-doanh-119260112105136458.htm",
    "https://xaydungchinhsach.chinhphu.vn/chinh-sach-thue-voi-ho-kinh-doanh-co-doanh-nam-thu-duoi-500-trieu-dong-119260401110929512.htm",
    "https://xaydungchinhsach.chinhphu.vn/huong-dan-nop-thue-theo-phuong-phap-tu-khai-thue-tu-nop-119260312143103213.htm",
]

REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (K4-L3B-RAG-Pipeline news crawler)"


async def _crawl_with_crawl4ai(url: str) -> dict:
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        title = (result.metadata or {}).get("title") or url
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "content_markdown": result.markdown or "",
        }


def _crawl_with_requests(url: str) -> dict:
    """Fallback không cần trình duyệt: requests + BeautifulSoup.

    Dùng khi Crawl4AI/Playwright chưa cài được (ví dụ trong sandbox không có
    quyền cài trình duyệt). Chất lượng trích xuất thô hơn Crawl4AI nhưng vẫn
    đúng schema output.
    """
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    content_markdown = "\n\n".join(text for text in paragraphs if text)

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": content_markdown,
    }


async def crawl_article(url: str) -> dict:
    """Crawl một URL và trả về dict theo schema news article."""
    try:
        article = await _crawl_with_crawl4ai(url)
    except Exception:
        # Crawl4AI/Playwright không sẵn sàng trong môi trường này -> fallback.
        article = await asyncio.to_thread(_crawl_with_requests, url)

    if not article.get("content_markdown", "").strip():
        raise ValueError(f"Empty content extracted from {url}")
    return article


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not ARTICLE_URLS:
        print(
            "ARTICLE_URLS đang rỗng. Điền >= 5 URL bài viết công khai, hoặc "
            f"đặt file JSON thủ công vào {DATA_DIR}."
        )

    saved = 0
    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
            saved += 1
        except Exception as error:
            print(f"Failed: {url} — {error}")

    existing = list(DATA_DIR.glob("*.json"))
    if len(existing) < 5:
        print(f"Cảnh báo: mới có {len(existing)} bài trong {DATA_DIR}, cần tối thiểu 5.")
    else:
        print(f"OK: {len(existing)} bài trong {DATA_DIR} (mới lưu {saved}).")


if __name__ == "__main__":
    asyncio.run(crawl_all())
