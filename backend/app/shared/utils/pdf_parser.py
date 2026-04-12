# backend/app/shared/utils/pdf_parser.py

"""
PDF text extraction and cleaning utilities.
"""

import re
from pypdf import PdfReader

from backend.app.constants import (
    PDF_NEWLINE_CLEANUP_PATTERN,
    PDF_BROKEN_WORD_PATTERN,
    PDF_EXTRA_SPACES_PATTERN,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract and clean raw text from a PDF file.

    Args:
        pdf_path: Local path to the PDF.

    Returns:
        Cleaned plain text.
    """
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content

    text = clean_text(text)
    logger.info(f"Extracted and cleaned text from {pdf_path}")
    return text


def clean_text(text: str) -> str:
    """
    Apply regex-based cleaning to raw PDF text:
    - Collapse multiple newlines.
    - Fix broken words across line breaks.
    - Reduce multiple spaces.

    Args:
        text: Raw text from PDF.

    Returns:
        Cleaned text.
    """
    # Remove excessive newlines
    text = re.sub(PDF_NEWLINE_CLEANUP_PATTERN, "\n", text)

    # Fix broken words from PDF (e.g., "sof-\ntware" -> "software")
    text = re.sub(PDF_BROKEN_WORD_PATTERN, r"\1\2", text)

    # Remove extra spaces
    text = re.sub(PDF_EXTRA_SPACES_PATTERN, " ", text)

    return text