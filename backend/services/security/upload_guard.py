"""Reusable helpers for validating uploaded files."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from typing import Iterable, Tuple

from fastapi import HTTPException, UploadFile, status

SAFE_FILENAME_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]")
_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".doc": (_OLE_SIGNATURE,),
    ".xls": (_OLE_SIGNATURE,),
    ".ppt": (_OLE_SIGNATURE,),
    ".docx": _ZIP_SIGNATURES,
    ".xlsx": _ZIP_SIGNATURES,
    ".pptx": _ZIP_SIGNATURES,
}
_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def _sanitize_filename(filename: str) -> str:
    """Remove unsafe characters to prevent path traversal."""
    sanitized = SAFE_FILENAME_PATTERN.sub("_", filename)
    return sanitized[:255] or secrets.token_hex(8)


def _looks_like_text(content: bytes) -> bool:
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    return True


def _content_matches_extension(content: bytes, extension: str) -> bool:
    ext = extension.lower()
    if ext in _TEXT_EXTENSIONS:
        return _looks_like_text(content)

    signatures = _SIGNATURES.get(ext)
    if not signatures:
        return True
    return any(content.startswith(sig) for sig in signatures)


async def validate_and_buffer_upload(
    upload: UploadFile,
    *,
    allowed_extensions: Iterable[str],
    max_bytes: int,
) -> Tuple[bytes, str]:
    """
    Validate filename/size before persisting.

    Returns:
        (file_content, sanitized_filename)
    """
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required."
        )

    original_name = upload.filename.strip()
    extension = Path(original_name).suffix.lower()
    if allowed_extensions and extension not in {
        ext.lower() for ext in allowed_extensions
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{extension}' is not allowed.",
        )

    content = await upload.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty files are not allowed.",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {max_bytes // (1024 * 1024)}MB.",
        )
    if not _content_matches_extension(content, extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match file extension signature.",
        )

    sanitized_name = _sanitize_filename(original_name)
    upload.file.seek(0)
    return content, sanitized_name


def persist_temp_file(content: bytes, filename: str, prefix: str = "upload") -> str:
    """Persist the validated content to an OS-managed temp directory."""
    temp_dir = Path(
        Path(os.getenv("TMPDIR", "/tmp")) / f"{prefix}_{secrets.token_hex(4)}"
    )
    temp_dir.mkdir(parents=True, exist_ok=True)
    file_path = temp_dir / filename
    with open(file_path, "wb") as buf:
        buf.write(content)
    return str(file_path)
