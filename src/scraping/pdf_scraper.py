"""PDF scraper: downloads and extracts text from dictionary and grammar PDFs."""

from pathlib import Path

import requests

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)

RAW_DIR = PROJECT_ROOT / "data" / "raw"


def download_pdf(url: str, filename: str) -> Path:
    """Download a PDF file from a URL.

    Args:
        url: Direct URL to the PDF file.
        filename: Name for the saved file.

    Returns:
        Path to the downloaded file.
    """
    pdf_dir = RAW_DIR / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    path = pdf_dir / filename

    if path.exists():
        log.info(f"PDF already downloaded: {path}")
        return path

    log.info(f"Downloading PDF: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, timeout=60, headers=headers)
    response.raise_for_status()

    with open(path, "wb") as f:
        f.write(response.content)

    log.info(f"Saved PDF: {path} ({len(response.content) / 1024:.1f} KB)")
    return path


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    import pdfplumber

    text_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_pages.append(page_text)
            else:
                log.warning(f"No text extracted from page {i + 1} of {pdf_path}")

    log.info(f"Extracted text from {len(text_pages)} pages of {pdf_path}")
    return "\n\n".join(text_pages)


def download_all_pdfs() -> list[Path]:
    """Download all configured PDF resources.

    Returns:
        List of paths to downloaded PDF files.
    """
    from src.utils.config import load_config

    config = load_config("scraping")
    paths = []

    for resource in config.get("pdf_resources", []):
        url = resource.get("url")
        filename = resource.get("filename")
        if url and filename:
            path = download_pdf(url, filename)
            paths.append(path)
        else:
            log.warning(f"Skipping PDF resource (missing url or filename): {resource}")

    return paths
