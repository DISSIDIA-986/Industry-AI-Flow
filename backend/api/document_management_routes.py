"""
文档管理API路由
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.audit_logger import audit_logger
from backend.services.core.vectorstore import VectorStore
from backend.services.document_manager import DocumentManager, DocumentOperation
from backend.services.security import persist_temp_file, validate_and_buffer_upload

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(secure_endpoint)])

# 全局文档管理器实例
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
    """获取文档管理器实例"""
    global document_manager
    if document_manager is None:
        vectorstore = VectorStore()
        document_manager = DocumentManager(vectorstore)
    return document_manager


class DocumentUpdateRequest(BaseModel):
    """文档更新请求模型"""

    doc_id: str
    reason: Optional[str] = None


class DocumentDeleteRequest(BaseModel):
    """文档删除请求模型"""

    doc_id: str
    reason: Optional[str] = None
    soft_delete: bool = True


class DocumentReplaceRequest(BaseModel):
    """文档替换请求模型"""

    doc_id: str
    reason: Optional[str] = None


class DocumentVersionResponse(BaseModel):
    """文档版本响应模型"""

    doc_id: str
    version: int
    filename: str
    filepath: str
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
    更新文档内容

    Args:
        file: 新文档文件
        doc_id: 文档ID
        reason: 更新原因

    Returns:
        更新结果
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    reason: str = None,
    soft_delete: bool = True,
    tenant: TenantContext = Depends(get_current_tenant),
):
    """
    删除文档

    Args:
        doc_id: 文档ID
        reason: 删除原因
        soft_delete: 是否软删除

    Returns:
        删除结果
    """
    try:
        if not settings.enable_document_deletion:
            raise HTTPException(status_code=403, detail="Document deletion is disabled")

        doc_manager = get_document_manager()
        success = doc_manager.delete_document(
            doc_id=doc_id, reason=reason, soft_delete=soft_delete
        )

        if success:
            delete_type = "soft deleted" if soft_delete else "permanently deleted"
            logger.info(f"Document {doc_id} {delete_type} successfully")
            _log_document_event(
                action="document.delete",
                tenant=tenant,
                status="success",
                detail={"doc_id": doc_id, "soft_delete": soft_delete},
            )
            return {
                "success": True,
                "message": f"Document {delete_type} successfully",
                "doc_id": doc_id,
                "delete_type": delete_type,
            }
        else:
            logger.warning(f"Failed to delete document {doc_id}")
            _log_document_event(
                action="document.delete",
                tenant=tenant,
                status="error",
                detail={"doc_id": doc_id, "reason": "delete_failed"},
            )
            return {
                "success": False,
                "message": "Failed to delete document",
                "doc_id": doc_id,
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/documents/replace")
async def replace_document(
    file: UploadFile = File(...),
    doc_id: str = Body(...),
    reason: str = Body(None),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """
    替换文档内容

    Args:
        file: 新文档文件
        doc_id: 原文档ID
        reason: 替换原因

    Returns:
        替换结果
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/documents/{doc_id}/versions", response_model=List[DocumentVersionResponse]
)
async def get_document_versions(doc_id: str):
    """
    获取文档的所有版本

    Args:
        doc_id: 文档ID

    Returns:
        文档版本列表
    """
    try:
        doc_manager = get_document_manager()
        versions = doc_manager.get_document_versions(doc_id)

        return [
            DocumentVersionResponse(
                doc_id=version.doc_id,
                version=version.version,
                filename=version.filename,
                filepath=version.filepath,
                chunk_count=version.chunk_count,
                created_at=version.created_at.isoformat(),
                operation=version.operation.value,
                is_active=version.is_active,
            )
            for version in versions
        ]

    except Exception as e:
        logger.error(f"Error getting document versions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/documents/operations/log")
async def get_operation_log(doc_id: str = None, limit: int = 50):
    """
    获取文档操作日志

    Args:
        doc_id: 文档ID（可选）
        limit: 返回数量限制

    Returns:
        操作日志列表
    """
    try:
        doc_manager = get_document_manager()
        logs = doc_manager.get_operation_log(doc_id=doc_id, limit=limit)

        return {"logs": logs, "count": len(logs), "doc_id": doc_id, "limit": limit}

    except Exception as e:
        logger.error(f"Error getting operation log: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/documents/statistics")
async def get_document_statistics():
    """
    获取文档统计信息

    Returns:
        文档统计信息
    """
    try:
        doc_manager = get_document_manager()
        stats = doc_manager.get_document_statistics()

        return stats

    except Exception as e:
        logger.error(f"Error getting document statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/documents/{doc_id}/restore/{version}")
async def restore_document_version(doc_id: str, version: int, reason: str = None):
    """
    恢复文档到指定版本

    Args:
        doc_id: 文档ID
        version: 版本号
        reason: 恢复原因

    Returns:
        恢复结果
    """
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
