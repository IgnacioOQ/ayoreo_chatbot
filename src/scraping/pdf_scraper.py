"""PDF scraper: extracts text from dictionary and grammar PDFs."""

from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)


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
