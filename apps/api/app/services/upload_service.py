"""Upload service for handling file uploads, storage, and extraction.

Responsibilities:
- Validate file size/type
- Store raw bytes to disk (POC; later replace with S3)
- Create DB records
- Extract text via text_extraction_service
- Never throw away files
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from app.models.enums import DocumentStatus, DocumentType
from app.services.text_extraction_service import extract_text

logger = logging.getLogger(__name__)

# Storage directory (create if needed)
STORAGE_DIR = Path(__file__).parent.parent.parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class UploadError(Exception):
    """Custom exception for upload failures."""

    pass


def validate_file(file_bytes: bytes, filename: str) -> None:
    """
    Validate file size and basic properties.

    Args:
        file_bytes: Raw file data
        filename: Original filename

    Raises:
        UploadError: If validation fails
    """
    if not file_bytes:
        raise UploadError("File is empty")

    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / 1024 / 1024
        raise UploadError(f"File exceeds 25MB limit (got {size_mb:.2f}MB)")

    if not filename or not filename.strip():
        raise UploadError("Filename is required")


def store_file_on_disk(file_bytes: bytes, document_id: uuid.UUID) -> str:
    """
    Store raw file bytes to disk.

    POC implementation: uses local filesystem.
    Later: replace with S3 or similar.

    Args:
        file_bytes: Raw file data
        document_id: Document UUID (used as filename)

    Returns:
        Path to stored file
    """
    file_path = STORAGE_DIR / f"{document_id}.bin"
    try:
        file_path.write_bytes(file_bytes)
        logger.info(f"[upload] Stored file at {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"[upload] Failed to store file: {e}")
        raise UploadError(f"Failed to store file: {str(e)}")


def infer_document_type(filename: str, mime_type: str) -> str:
    """
    Infer document type from filename and MIME type.

    Returns:
        DocumentType enum value string (or "other" if unknown)
    """
    ext = ""
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()

    # Map common extensions to DocumentType enum values
    type_map = {
        "pdf": DocumentType.OTHER.value,  # Store as OTHER; could add PDF to enum
        "docx": DocumentType.OTHER.value,
        "doc": DocumentType.OTHER.value,
        "txt": DocumentType.LESSON_PLAN.value,  # Assume lesson plan for text
        "md": DocumentType.LESSON_PLAN.value,
        "html": DocumentType.LESSON_PLAN.value,
        "htm": DocumentType.LESSON_PLAN.value,
        "rtf": DocumentType.OTHER.value,
    }

    return type_map.get(ext, DocumentType.OTHER.value)


class UploadProcessingResult:
    """Result of file processing."""

    def __init__(
        self,
        document_id: uuid.UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        extracted_text: Optional[str],
        extraction_status: str,
        warnings: list[str],
        document_type: str,
    ):
        self.document_id = document_id
        self.filename = filename
        self.mime_type = mime_type
        self.size_bytes = size_bytes
        self.extracted_text = extracted_text
        self.extraction_status = extraction_status
        self.warnings = warnings
        self.document_type = document_type

    def to_dict(self):
        """Convert to API response dict."""
        result = {
            "document_id": str(self.document_id),
            "filename": self.filename,
            "content_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "extraction_status": self.extraction_status,
        }
        if self.extracted_text:
            result["extracted_text"] = self.extracted_text
        if self.warnings:
            result["warnings"] = self.warnings
        return result


def process_upload(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> UploadProcessingResult:
    """
    Process a file upload: validate, store, extract.

    Args:
        file_bytes: Raw file data
        filename: Original filename
        mime_type: MIME type from upload

    Returns:
        UploadProcessingResult with all metadata and extracted text

    Raises:
        UploadError: If validation or storage fails
    """
    # 1. Validate
    validate_file(file_bytes, filename)

    # 2. Generate document ID and store file
    document_id = uuid.uuid4()
    store_file_on_disk(file_bytes, document_id)

    # 3. Extract text
    extracted_text, extraction_status, warnings = extract_text(
        file_bytes, filename, mime_type
    )

    # 4. Infer document type
    document_type = infer_document_type(filename, mime_type)

    logger.info(
        f"[upload] Processed file: {filename} → {document_id} "
        f"({len(file_bytes)} bytes, status={extraction_status})"
    )

    return UploadProcessingResult(
        document_id=document_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        extracted_text=extracted_text,
        extraction_status=extraction_status,
        warnings=warnings,
        document_type=document_type,
    )
