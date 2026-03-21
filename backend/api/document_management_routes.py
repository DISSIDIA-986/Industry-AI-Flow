"""
Document management API routes
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.audit_logger import audit_logger
from backend.services.core.vectorstore import VectorStore
from backend.services.document_manager import DocumentManager, DocumentOperation
from backend.services.security import persist_temp_file, validate_and_buffer_upload

import json
import asyncio
from fastapi.responses import StreamingResponse
from backend.services.document_processing.progress_tracker import (
    PipelineProgressTracker,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(secure_endpoint)])

# EN
document_manager = None
ALLOWED_DOC_EXTENSIONS = tuple(settings.upload_extension_whitelist)
MAX_UPLOAD_BYTES = settings.max_upload_size_bytes


def _log_document_event(
    action: str,
    tenant: Optional[TenantContext],
    status: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    tenant_id = tenant.tenant_id if tenant else settings.default_tenant_id
    audit_logger.log_event(
        action=action,
        tenant_id=tenant_id,
        status=status,
        user_id=tenant.user_id if tenant else None,
        ip_address=tenant.ip_address if tenant else None,
        detail=detail,
    )


def get_document_manager():
    """Document API schema."""
    global document_manager
    if document_manager is None:
        vectorstore = VectorStore()
        document_manager = DocumentManager(vectorstore)
    return document_manager


class DocumentUpdateRequest(BaseModel):
    """Document API schema."""

    doc_id: str
    reason: Optional[str] = None


class DocumentDeleteRequest(BaseModel):
    """Document API schema."""

    doc_id: str
    reason: Optional[str] = None
    soft_delete: bool = True


class DocumentReplaceRequest(BaseModel):
    """Document API schema."""

    doc_id: str
    reason: Optional[str] = None


class DocumentVersionResponse(BaseModel):
    """Document API schema."""

    doc_id: str
    version: int
    filename: str
    filepath: Optional[str] = None  # Redacted: server paths not exposed to clients
    chunk_count: int
    created_at: str
    operation: str
    is_active: bool


@router.post("/documents/update")
async def update_document(
    file: UploadFile = File(...),
    doc_id: str = Body(...),
    reason: str = Body(None),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """
    EN

    Args:
        file: EN
        doc_id: ENID
        reason: EN

    Returns:
        EN
    """
    try:
        if not settings.enable_document_update:
            raise HTTPException(status_code=403, detail="Document update is disabled")

        content, safe_name = await validate_and_buffer_upload(
            file,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        temp_file_path = persist_temp_file(content, safe_name, prefix="doc_update")

        try:
            doc_manager = get_document_manager()
            success = doc_manager.update_document(
                doc_id=doc_id, new_filepath=temp_file_path, reason=reason
            )

            if success:
                logger.info(
                    f"Document {doc_id} updated successfully with file {file.filename}"
                )
                _log_document_event(
                    action="document.update",
                    tenant=tenant,
                    status="success",
                    detail={"doc_id": doc_id, "filename": safe_name},
                )
                return {
                    "success": True,
                    "message": "Document updated successfully",
                    "doc_id": doc_id,
                    "filename": file.filename,
                }
            else:
                logger.warning(f"Failed to update document {doc_id}")
                _log_document_event(
                    action="document.update",
                    tenant=tenant,
                    status="error",
                    detail={"doc_id": doc_id, "reason": "update_failed"},
                )
                return {
                    "success": False,
                    "message": "Failed to update document",
                    "doc_id": doc_id,
                }

        finally:
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    except HTTPException:
        _log_document_event(
            action="document.update",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "reason": "validation_failed"},
        )
        raise
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        _log_document_event(
            action="document.update",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    reason: str = None,
    soft_delete: bool = True,
    tenant: TenantContext = Depends(get_current_tenant),
):
    """Delete a document — cleans up uploaded_documents_index, vector data, and disk file."""
    import re
    from pathlib import Path

    try:
        if not settings.enable_document_deletion:
            raise HTTPException(status_code=403, detail="Document deletion is disabled")

        deleted_sources: list[str] = []
        tenant_id = tenant.tenant_id
        conn = VectorStore().get_connection()
        cur = conn.cursor()

        try:
            # 1. Clean uploaded_documents_index
            file_path_to_remove: str | None = None
            cur.execute(
                "SELECT file_path, original_filename FROM uploaded_documents_index "
                "WHERE id = %s AND tenant_id = %s",
                (doc_id, tenant_id),
            )
            upload_row = cur.fetchone()
            if upload_row:
                file_path_to_remove = upload_row[0]
                cur.execute(
                    "DELETE FROM uploaded_documents_index WHERE id = %s AND tenant_id = %s",
                    (doc_id, tenant_id),
                )
                deleted_sources.append("uploaded_index")

            # 2. Try direct match in documents table (UUID-based doc_id)
            cur.execute("SELECT id, filepath FROM documents WHERE id = %s", (doc_id,))
            doc_row = cur.fetchone()
            if doc_row:
                if not file_path_to_remove:
                    file_path_to_remove = doc_row[1]
                cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))
                cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                deleted_sources.append("vector_index")

            # 3. For uploaded_index IDs (doc-xxx), find vector data by matching filename
            if "vector_index" not in deleted_sources and file_path_to_remove:
                fname = Path(file_path_to_remove).name
                clean_name = re.sub(r"_[a-f0-9]{12}(\.\w+)$", r"\1", fname)
                cur.execute("SELECT id FROM documents WHERE filename = %s", (clean_name,))
                vec_row = cur.fetchone()
                if vec_row:
                    vec_doc_id = vec_row[0]
                    cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (vec_doc_id,))
                    cur.execute("DELETE FROM documents WHERE id = %s", (vec_doc_id,))
                    deleted_sources.append("vector_index")

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

        # 4. Remove file from disk
        if file_path_to_remove:
            try:
                fp = Path(file_path_to_remove)
                if fp.exists():
                    os.unlink(fp)
                    deleted_sources.append("disk")
            except Exception as exc:
                logger.warning("Failed to remove file %s: %s", file_path_to_remove, exc)

        if not deleted_sources:
            # Fall back to DocumentManager for legacy documents
            doc_manager = get_document_manager()
            success = doc_manager.delete_document(
                doc_id=doc_id, reason=reason, soft_delete=soft_delete
            )
            if success:
                deleted_sources.append("vector_index")

        if not deleted_sources:
            _log_document_event(
                action="document.delete",
                tenant=tenant,
                status="error",
                detail={"doc_id": doc_id, "reason": "not_found"},
            )
            return {"success": False, "message": "Document not found", "doc_id": doc_id}

        logger.info("Document %s deleted from: %s", doc_id, deleted_sources)
        _log_document_event(
            action="document.delete",
            tenant=tenant,
            status="success",
            detail={"doc_id": doc_id, "deleted_from": deleted_sources},
        )
        return {
            "success": True,
            "message": f"Document deleted from: {', '.join(deleted_sources)}",
            "doc_id": doc_id,
            "deleted_from": deleted_sources,
        }

    except HTTPException:
        _log_document_event(
            action="document.delete",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "reason": "validation_failed"},
        )
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        _log_document_event(
            action="document.delete",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/replace")
async def replace_document(
    file: UploadFile = File(...),
    doc_id: str = Body(...),
    reason: str = Body(None),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """
    EN

    Args:
        file: EN
        doc_id: ENID
        reason: EN

    Returns:
        EN
    """
    try:
        content, safe_name = await validate_and_buffer_upload(
            file,
            allowed_extensions=ALLOWED_DOC_EXTENSIONS,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        temp_file_path = persist_temp_file(content, safe_name, prefix="doc_replace")

        try:
            doc_manager = get_document_manager()
            success = doc_manager.replace_document(
                doc_id=doc_id, new_filepath=temp_file_path, reason=reason
            )

            if success:
                logger.info(
                    f"Document {doc_id} replaced successfully with file {file.filename}"
                )
                _log_document_event(
                    action="document.replace",
                    tenant=tenant,
                    status="success",
                    detail={"doc_id": doc_id, "filename": safe_name},
                )
                return {
                    "success": True,
                    "message": "Document replaced successfully",
                    "doc_id": doc_id,
                    "filename": file.filename,
                }
            else:
                logger.warning(f"Failed to replace document {doc_id}")
                _log_document_event(
                    action="document.replace",
                    tenant=tenant,
                    status="error",
                    detail={"doc_id": doc_id, "reason": "replace_failed"},
                )
                return {
                    "success": False,
                    "message": "Failed to replace document",
                    "doc_id": doc_id,
                }

        finally:
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    except HTTPException:
        _log_document_event(
            action="document.replace",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "reason": "validation_failed"},
        )
        raise
    except Exception as e:
        logger.error(f"Error replacing document: {e}")
        _log_document_event(
            action="document.replace",
            tenant=tenant,
            status="error",
            detail={"doc_id": doc_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/documents/{doc_id}/versions", response_model=List[DocumentVersionResponse]
)
async def get_document_versions(doc_id: str):
    """
    EN

    Args:
        doc_id: ENID

    Returns:
        EN
    """
    try:
        doc_manager = get_document_manager()
        versions = doc_manager.get_document_versions(doc_id)

        return [
            DocumentVersionResponse(
                doc_id=version.doc_id,
                version=version.version,
                filename=version.filename,
                filepath=None,  # Server path redacted for security
                chunk_count=version.chunk_count,
                created_at=version.created_at.isoformat(),
                operation=version.operation.value,
                is_active=version.is_active,
            )
            for version in versions
        ]

    except Exception as e:
        logger.error(f"Error getting document versions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/operations/log")
async def get_operation_log(doc_id: str = None, limit: int = 50):
    """
    EN

    Args:
        doc_id: ENID(EN)
        limit: EN

    Returns:
        EN
    """
    limit = min(limit, 500)
    try:
        doc_manager = get_document_manager()
        logs = doc_manager.get_operation_log(doc_id=doc_id, limit=limit)

        return {"logs": logs, "count": len(logs), "doc_id": doc_id, "limit": limit}

    except Exception as e:
        logger.error(f"Error getting operation log: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/statistics")
async def get_document_statistics():
    """
    EN

    Returns:
        EN
    """
    try:
        doc_manager = get_document_manager()
        stats = doc_manager.get_document_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting document statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/{doc_id}/restore/{version}")
async def restore_document_version(
    doc_id: str,
    version: int,
    reason: str = None,
    request: Request = None,
    tenant: "TenantContext" = Depends(get_current_tenant),
):
    """
    Restore a document to a specific version.

    Args:
        doc_id: Document ID
        version: Target version number
        reason: Reason for restore

    Returns:
        Restore result
    """
    tenant_id = (
        tenant.tenant_id
        if tenant
        else (request.headers.get("X-Tenant-ID", "") if request else "")
    )
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant identification required")

    try:
        doc_manager = get_document_manager()
        success = doc_manager.restore_document_version(
            doc_id=doc_id, version=version, reason=reason
        )

        if success:
            logger.info(f"Document {doc_id} restored to version {version}")
            return {
                "success": True,
                "message": "Document version restored successfully",
                "doc_id": doc_id,
                "version": version,
            }
        else:
            logger.warning(f"Failed to restore document {doc_id} to version {version}")
            return {
                "success": False,
                "message": "Failed to restore document version",
                "doc_id": doc_id,
                "version": version,
            }

    except Exception as e:
        logger.error(f"Error restoring document version: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{doc_id}/progress")
async def document_progress_stream(doc_id: str):
    """Stream pipeline progress events via SSE (no auth required for demo)."""
    tracker = PipelineProgressTracker.get(doc_id)

    async def event_generator():
        if tracker is None or tracker.async_queue is None:
            # No active pipeline for this doc — send a done event
            yield f"data: {json.dumps({'stage': 'unknown', 'status': 'completed', 'progress': 1.0, 'detail': 'Already processed', 'elapsed_ms': 0})}\n\n"
            return

        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        tracker.async_queue.get(), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    # Sentinel — pipeline complete or failed
                    return

                yield f"data: {json.dumps(event.to_dict())}\n\n"
        except asyncio.CancelledError:
            return
        finally:
            tracker.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
