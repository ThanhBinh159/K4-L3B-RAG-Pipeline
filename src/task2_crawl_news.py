"""Collect official household-business guides as source-attributed JSON."""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "landing" / "news"
ARTICLE_SOURCES = {
    "dang_ky_ho_kinh_doanh": "https://xaydungchinhsach.chinhphu.vn/quy-dinh-ho-so-trinh-tu-thu-tuc-dang-ky-thanh-lap-ho-kinh-doanh-119250702172916754.htm",
    "tu_khai_tu_nop_thue": "https://xaydungchinhsach.chinhphu.vn/huong-dan-nop-thue-theo-phuong-phap-tu-khai-thue-tu-nop-119260312143103213.htm",
    "ke_toan_ho_kinh_doanh": "https://xaydungchinhsach.chinhphu.vn/toan-van-thong-tu-152-2025-tt-bt-huong-dan-ke-toan-cho-cac-ho-kinh-doanh-ca-nhan-kinh-doanh-119260112105136458.htm",
    "thue_doanh_thu_duoi_500_trieu": "https://xaydungchinhsach.chinhphu.vn/chinh-sach-thue-voi-ho-kinh-doanh-co-doanh-nam-thu-duoi-500-trieu-dong-119260401110929512.htm",
    "hoa_don_giam_thue_gtgt": "https://xaydungchinhsach.chinhphu.vn/truong-hop-duoc-giam-thue-gtgt-ho-kinh-doanh-lap-hoa-don-ke-khai-thue-nhu-the-nao-119260423055529827.htm",
    "bieu_mau_dang_ky_2026": "https://xaydungchinhsach.chinhphu.vn/bieu-mau-dang-ky-ho-kinh-doanh-11926091009173649.htm",
}
ARTICLE_URLS = list(ARTICLE_SOURCES.values())


def extract_article(html: str, url: str, crawled: str) -> dict:
    """Read only the article body and stop before related-story links."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("div.detail-content.afcbc-body") or soup.select_one("article")
    if body is None:
        raise ValueError(f"Article body unavailable: {url}")
    title_node = soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    if not title:
        raise ValueError(f"Article title unavailable: {url}")
    paragraphs = []
    for node in body.find_all(["p", "h2", "h3", "h4", "li"]):
        value = node.get_text(" ", strip=True)
        if value.startswith("Tham khảo thêm"):
            break
        if not value or (paragraphs and paragraphs[-1] == value):
            continue
        prefix = "## " if node.name in {"h2", "h3", "h4"} else "- " if node.name == "li" else ""
        paragraphs.append(prefix + value)
    content = "\n\n".join(paragraphs).strip()
    if not content:
        raise ValueError(f"Article text unavailable: {url}")
    return {"url": url, "title": title, "date_crawled": crawled, "content_markdown": content}


async def crawl_article(url: str) -> dict:
    """Fetch a public source with a finite timeout."""
    response = await asyncio.to_thread(requests.get, url, timeout=30)
    response.raise_for_status()
    return extract_article(response.text, url, date.today().isoformat())


async def crawl_all(*, refresh: bool = False) -> None:
    """Reuse valid snapshots unless a caller explicitly requests refresh."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for slug, url in ARTICLE_SOURCES.items():
        output = DATA_DIR / f"{slug}.json"
        if output.exists() and not refresh:
            try:
                existing = json.loads(output.read_text(encoding="utf-8"))
                if existing.get("url") == url and all(existing.get(key) for key in ("title", "date_crawled", "content_markdown")):
                    print(f"Reused: {output}")
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        article = await crawl_article(url)
        output.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved: {output}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch all pages again")
    args = parser.parse_args()
    asyncio.run(crawl_all(refresh=args.refresh))
