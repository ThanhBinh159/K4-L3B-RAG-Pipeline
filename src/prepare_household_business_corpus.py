"""Export a focused household-business subset of Vietnam laws IR.

Run ``python -m src.prepare_household_business_corpus --download`` to fetch the
pinned corpus and write Markdown documents for the project's RAG pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.request import urlretrieve


DATASET_ID = "justicedao/ipfs_vietnam_laws_ir"
DATASET_REVISION = "89013dcc37dea35d0d858b2f07517bf425f76729"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE = REPO_ROOT / ".cache" / "hf_vietnam_laws_corpus"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "standardized" / "legal"

# Reviewed article numbers; this corpus alone does not cover every obligation.
SELECTION = {
    "vn-61635": ("hkd_quan_ly_thue_108_2025", "Luật Quản lý thuế 108/2025/QH15", {2, 4, 10, 11, 13, 17, 20, 21, 26, 52}),
    "vn-61623": ("hkd_thue_thu_nhap_ca_nhan_109_2025", "Luật Thuế thu nhập cá nhân 109/2025/QH15", {2, 3, 6, 7, 20, 29}),
    "vn-luat-so-48-2024-qh15-43576": ("hkd_thue_gia_tri_gia_tang_48_2024", "Luật Thuế giá trị gia tăng 48/2024/QH15", {2, 4, 6, 7, 8, 9, 10, 12, 16, 18}),
    "vn-18418": ("hkd_ho_tro_doanh_nghiep_nho_va_vua_04_2017", "Luật Hỗ trợ doanh nghiệp nhỏ và vừa 04/2017/QH14", {4, 10, 14, 16, 34}),
    "vn-luat-bao-ve-quyen-loi-nguoi-tieu-dung-so-19-2023-qh15": ("hkd_bao_ve_nguoi_tieu_dung_19_2023", "Luật Bảo vệ quyền lợi người tiêu dùng 19/2023/QH15", {3, 9, 10, 14, 21, 29, 30, 31, 37, 39, 54, 79}),
    "vn-1214": ("hkd_an_toan_thuc_pham_55_2010", "Luật An toàn thực phẩm 55/2010/QH12", {7, 8, 19, 24, 27, 28, 29, 31, 34, 36, 71}),
}


def select_articles(rows: list[dict], selection: dict[str, set[int]]) -> dict[str, list[dict]]:
    """Select whole, named articles and deduplicate alternate source URLs."""
    chosen: dict[str, dict[int, dict]] = {instrument_id: {} for instrument_id in selection}
    for row in rows:
        instrument_id = row.get("instrument_id")
        if instrument_id not in selection:
            continue
        match = re.fullmatch(r"Điều\s+(\d+)", str(row.get("article_number", "")))
        if not match:
            continue
        number = int(match.group(1))
        if number not in selection[instrument_id]:
            continue
        # The upstream extraction occasionally emits references such as
        # "Điều 10 của Luật..." as a second, false article row.
        opening = f"Điều {number}."
        if not str(row.get("article_title", "")).startswith(opening):
            continue
        if not str(row.get("body", "")).startswith(opening):
            continue
        existing = chosen[instrument_id].get(number)
        if existing is None or (len(row.get("source_url") or ""), row.get("source_url") or "") < (
            len(existing.get("source_url") or ""), existing.get("source_url") or ""
        ):
            chosen[instrument_id][number] = row
    return {
        instrument_id: [articles[number] for number in sorted(articles)]
        for instrument_id, articles in chosen.items()
    }


def render_law_markdown(rows: list[dict], dataset_revision: str, display_title: str | None = None) -> str:
    """Keep the original article text with traceable citation fields."""
    if not rows:
        raise ValueError("Cannot render an empty law")
    first = rows[0]
    title = display_title or first["instrument_title"]
    parts = [
        f"# {title}",
        "",
        f"**Nguồn chính thức:** {first['source_url']}",
        f"**Dataset:** https://huggingface.co/datasets/{DATASET_ID}",
        f"**Dataset revision:** {dataset_revision}",
        f"**Source revision:** {first.get('source_revision', '')}",
        f"**Snapshot date:** {first.get('snapshot_date', '')}",
        "**Phạm vi:** Các điều được chọn cho RAG về hộ kinh doanh; kiểm tra hiệu lực tại nguồn chính thức trước khi tư vấn.",
    ]
    for row in rows:
        parts.extend((
            "",
            f"## {row['article_title']}",
            f"**Entry CID:** {row.get('entry_cid', '')}",
            "",
            row["body"].strip(),
        ))
    return "\n".join(parts) + "\n"


def download_corpus(cache_dir: Path) -> list[Path]:
    """Download only the corpus shards, not prebuilt indexes or vectors."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in range(11):
        filename = f"part-{index:06d}.parquet"
        path = cache_dir / filename
        if not path.exists() or path.stat().st_size == 0:
            url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{DATASET_REVISION}/data/corpus/{filename}"
            urlretrieve(url, path)
        paths.append(path)
    return paths


def export_corpus(cache_dir: Path, output_dir: Path) -> dict:
    import pyarrow.parquet as parquet

    files = sorted(cache_dir.glob("part-*.parquet"))
    if len(files) != 11:
        raise FileNotFoundError("Expected 11 corpus shards; run with --download")
    rows = [row for path in files for row in parquet.read_table(path).to_pylist()]
    selected = select_articles(rows, {key: spec[2] for key, spec in SELECTION.items()})
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": DATASET_ID, "dataset_revision": DATASET_REVISION, "source_rows": len(rows), "documents": []}
    for instrument_id, (slug, display_title, numbers) in SELECTION.items():
        articles = selected[instrument_id]
        found = {int(row["article_number"].split()[1]) for row in articles}
        if found != numbers:
            raise ValueError(f"Missing valid articles for {instrument_id}: {sorted(numbers - found)}")
        filename = f"{slug}.md"
        (output_dir / filename).write_text(
            render_law_markdown(articles, DATASET_REVISION, display_title), encoding="utf-8"
        )
        manifest["documents"].append({
            "file": filename,
            "instrument_id": instrument_id,
            "title": display_title,
            "source_url": articles[0]["source_url"],
            "snapshot_date": articles[0].get("snapshot_date"),
            "articles": [row["article_number"] for row in articles],
            "entry_cids": [row.get("entry_cid") for row in articles],
        })
    (output_dir / "hkd_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download the pinned Hugging Face corpus")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.download:
        download_corpus(args.cache_dir)
    manifest = export_corpus(args.cache_dir, args.output_dir)
    print(f"Exported {len(manifest['documents'])} laws and {sum(len(d['articles']) for d in manifest['documents'])} articles to {args.output_dir}")


if __name__ == "__main__":
    main()
