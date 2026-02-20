from __future__ import annotations

import io

import pytest
from fastapi import HTTPException, UploadFile

from backend.services.security.upload_guard import validate_and_buffer_upload


@pytest.mark.asyncio
async def test_validate_upload_accepts_pdf_signature() -> None:
    payload = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n"
    upload = UploadFile(filename="sample.pdf", file=io.BytesIO(payload))

    content, safe_name = await validate_and_buffer_upload(
        upload,
        allowed_extensions=[".pdf"],
        max_bytes=1024 * 1024,
    )

    assert content == payload
    assert safe_name.endswith(".pdf")


@pytest.mark.asyncio
async def test_validate_upload_rejects_mismatched_signature() -> None:
    payload = b"this is plain text but extension says pdf"
    upload = UploadFile(filename="malicious.pdf", file=io.BytesIO(payload))

    with pytest.raises(HTTPException) as exc_info:
        await validate_and_buffer_upload(
            upload,
            allowed_extensions=[".pdf"],
            max_bytes=1024 * 1024,
        )

    assert exc_info.value.status_code == 400
    assert "signature" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_validate_upload_accepts_zip_backed_docx() -> None:
    payload = b"PK\x03\x04\x14\x00\x00\x00\x00\x00"
    upload = UploadFile(filename="brief.docx", file=io.BytesIO(payload))

    content, safe_name = await validate_and_buffer_upload(
        upload,
        allowed_extensions=[".docx"],
        max_bytes=1024 * 1024,
    )

    assert content == payload
    assert safe_name.endswith(".docx")
