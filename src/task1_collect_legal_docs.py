"""Task 1 — Kiểm tra tài liệu legal đã thu thập thủ công."""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def validate_documents(minimum: int = 3) -> int:
    """Validate manually collected PDF/DOC/DOCX files without downloading."""
    files = sorted(
        path for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    ) if DATA_DIR.is_dir() else []
    if len(files) < minimum:
        raise RuntimeError(f"Expected at least {minimum} legal documents, found {len(files)}")
    invalid = [path.name for path in files if path.stat().st_size <= 1024]
    if invalid:
        raise RuntimeError(f"Legal documents are too small: {', '.join(invalid)}")
    return len(files)


if __name__ == "__main__":
    setup_directory()
    print(f"Validated {validate_documents()} manually collected legal documents")
