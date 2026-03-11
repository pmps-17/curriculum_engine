"""Text extraction service for various document formats.

Pure extraction logic with no database dependencies.
Supports: PDF, DOCX, TXT, MD, HTML.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def extract_text_from_pdf(data: bytes) -> Tuple[Optional[str], list[str]]:
    """
    Extract text from PDF bytes.

    Args:
        data: Raw PDF file bytes

    Returns:
        Tuple of (extracted_text, warnings)
    """
    warnings = []
    try:
        from pypdf import PdfReader
        from io import BytesIO

        pdf = PdfReader(BytesIO(data))
        text_parts = []

        for page_num, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            except Exception as e:
                warnings.append(f"Failed to extract page {page_num}: {str(e)}")

        extracted_text = "\n".join(text_parts) if text_parts else None
        return extracted_text, warnings

    except Exception as e:
        logger.error(f"[extraction] PDF extraction failed: {e}")
        return None, [f"PDF extraction failed: {str(e)}"]


def extract_text_from_docx(data: bytes) -> Tuple[Optional[str], list[str]]:
    """
    Extract text from DOCX bytes.

    Args:
        data: Raw DOCX file bytes

    Returns:
        Tuple of (extracted_text, warnings)
    """
    warnings = []
    try:
        from docx import Document
        from io import BytesIO

        doc = Document(BytesIO(data))
        text_parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        extracted_text = "\n".join(text_parts) if text_parts else None
        return extracted_text, warnings

    except Exception as e:
        logger.error(f"[extraction] DOCX extraction failed: {e}")
        return None, [f"DOCX extraction failed: {str(e)}"]


def extract_text_from_plain(data: bytes) -> Tuple[Optional[str], list[str]]:
    """
    Extract text from TXT/MD/HTML as UTF-8.

    Args:
        data: Raw file bytes

    Returns:
        Tuple of (extracted_text, warnings)
    """
    warnings = []
    try:
        # Try UTF-8 first, then fall back to latin-1
        try:
            text = data.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace").strip()

        return text if text else None, warnings

    except Exception as e:
        logger.error(f"[extraction] Plain text extraction failed: {e}")
        return None, [f"Text extraction failed: {str(e)}"]


def extract_text(
    file_bytes: bytes, filename: str, mime_type: str
) -> Tuple[Optional[str], str, list[str]]:
    """
    Intelligently extract text from various document formats.

    Args:
        file_bytes: Raw file data
        filename: Original filename (used to infer type)
        mime_type: MIME type from upload

    Returns:
        Tuple of (extracted_text, extraction_status, warnings)
        Status: "EXTRACTED" | "STORED_ONLY" | "REJECTED"
    """
    if not file_bytes:
        return None, "REJECTED", ["File is empty"]

    # Infer type from filename extension
    ext = ""
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()

    # Route to appropriate extractor
    if ext == "pdf" or "pdf" in mime_type.lower():
        text, warnings = extract_text_from_pdf(file_bytes)
        status = "EXTRACTED" if text else "STORED_ONLY"
        return text, status, warnings

    elif ext in ("docx", "doc") or "wordprocessingml" in mime_type.lower():
        text, warnings = extract_text_from_docx(file_bytes)
        status = "EXTRACTED" if text else "STORED_ONLY"
        return text, status, warnings

    elif ext in ("txt", "md", "markdown", "html", "htm") or mime_type.startswith(
        "text/"
    ):
        text, warnings = extract_text_from_plain(file_bytes)
        status = "EXTRACTED" if text else "STORED_ONLY"
        return text, status, warnings

    else:
        # Unknown format: store only
        return None, "STORED_ONLY", []
