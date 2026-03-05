"""
Document Manager - Handles document CRUD operations with version tracking.
"""

import datetime
import logging
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from backend.config import settings
from backend.services.core.chunker import DocumentChunker
from backend.services.core.embedder import embed_single_text
from backend.services.core.vectorstore import VectorStore
from backend.services.document_loader import DocumentLoader
from backend.services.retrieval.document_profile import DocumentProfileService

logger = logging.getLogger(__name__)


class DocumentOperation(Enum):
    """Types of document operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REPLACE = "replace"


@dataclass
class DocumentVersion:
    """Represents a specific version of a document."""

    doc_id: str
    version: int
    filename: str
    filepath: str
    chunk_count: int
    created_at: datetime.datetime
    operation: DocumentOperation
    is_active: bool = True


class DocumentManager:
    """Document Manager - Provides full CRUD operations with version control."""

    def __init__(self, vectorstore: VectorStore):
        self.vectorstore = vectorstore
        self.document_loader = DocumentLoader()
        self.chunker = DocumentChunker()
        self.document_profile_service = DocumentProfileService(vectorstore)
        self._init_database()

    def _refresh_profile_best_effort(self, doc_id: str) -> None:
        try:
            self.document_profile_service.refresh_profile_for_document(doc_id)
        except Exception as exc:  # pragma: no cover - runtime best effort
            logger.warning("Failed to refresh document profile for %s: %s", doc_id, exc)

    def _remove_profile_best_effort(self, doc_id: str) -> None:
        try:
            self.document_profile_service.remove_profile(doc_id)
        except Exception as exc:  # pragma: no cover - runtime best effort
            logger.warning("Failed to remove document profile for %s: %s", doc_id, exc)

    def _init_database(self):
        """Initialize document management database tables."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Create document versions table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_versions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    doc_id VARCHAR(255) NOT NULL,
                    version INTEGER NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    filepath TEXT,
                    chunk_count INTEGER NOT NULL,
                    operation VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE (doc_id, version)
                )
            """
            )

            # Create operations log table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_operations_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    doc_id VARCHAR(255),
                    operation VARCHAR(50) NOT NULL,
                    filename VARCHAR(255),
                    old_filename VARCHAR(255),
                    reason TEXT,
                    status VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create version management trigger function
            cur.execute(
                """
                CREATE OR REPLACE FUNCTION update_document_versions()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Deactivate previous versions
                    UPDATE document_versions
                    SET is_active = FALSE
                    WHERE doc_id = NEW.doc_id AND is_active = TRUE AND version != NEW.version;

                    -- Return the new row
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """
            )

            # Create the trigger
            cur.execute(
                """
                DROP TRIGGER IF EXISTS trigger_update_document_versions ON document_versions;
                CREATE TRIGGER trigger_update_document_versions
                    AFTER INSERT ON document_versions
                    FOR EACH ROW
                    EXECUTE FUNCTION update_document_versions();
            """
            )

            # Create indexes
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(doc_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_versions_active ON document_versions(is_active)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_operations_created ON document_operations_log(created_at)"
            )

            conn.commit()
            logger.info("Document management database tables initialized successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize document management database: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def update_document(
        self, doc_id: str, new_filepath: str, reason: str = None
    ) -> bool:
        """
        Update an existing document with new content.

        Args:
            doc_id: Document ID to update.
            new_filepath: Path to the new document file.
            reason: Reason for the update.

        Returns:
            True if the update was successful, False otherwise.
        """
        if not settings.enable_document_update:
            logger.warning("Document update is disabled")
            return False

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Look up existing document
            cur.execute(
                "SELECT filename, filepath FROM documents WHERE id = %s", (doc_id,)
            )
            existing_doc = cur.fetchone()

            if not existing_doc:
                logger.error(f"Document {doc_id} not found")
                return False

            old_filename, old_filepath = existing_doc

            # Verify new file exists
            if not os.path.exists(new_filepath):
                logger.error(f"New file not found: {new_filepath}")
                return False

            # Get current version number
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM document_versions WHERE doc_id = %s",
                (doc_id,),
            )
            current_version = cur.fetchone()[0]
            new_version = current_version + 1

            # Process the new document
            try:
                # Load and chunk the new file
                new_filename = os.path.basename(new_filepath)
                documents = self.document_loader.load_document(new_filepath)
                if not documents:
                    raise ValueError(f"No content loaded from {new_filepath}")

                # Split into chunks
                chunks = []
                for doc in documents:
                    doc_chunks = self.chunker.chunk_document(doc)
                    chunks.extend([chunk.page_content for chunk in doc_chunks])

                if not chunks:
                    raise ValueError(f"No chunks generated from {new_filepath}")

                # Generate embeddings for each chunk
                embeddings = [embed_single_text(chunk) for chunk in chunks]

            except Exception as e:
                logger.error(f"Failed to process new document: {e}")
                self._log_operation(
                    doc_id,
                    DocumentOperation.UPDATE,
                    new_filename,
                    old_filename,
                    reason,
                    "failed",
                    str(e),
                )
                return False

            # Delete old chunks
            cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))

            # Insert new chunks with embeddings
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO document_chunks (doc_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                """,
                    (doc_id, i, chunk, embedding),
                )

            # Update document metadata
            cur.execute(
                """
                UPDATE documents
                SET filename = %s, filepath = %s, chunk_count = %s
                WHERE id = %s
            """,
                (new_filename, new_filepath, len(chunks), doc_id),
            )

            # Record new version
            cur.execute(
                """
                INSERT INTO document_versions (doc_id, version, filename, filepath, chunk_count, operation, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            """,
                (
                    doc_id,
                    new_version,
                    new_filename,
                    new_filepath,
                    len(chunks),
                    DocumentOperation.UPDATE.value,
                ),
            )

            conn.commit()
            self._refresh_profile_best_effort(doc_id)

            # Log successful operation
            self._log_operation(
                doc_id,
                DocumentOperation.UPDATE,
                new_filename,
                old_filename,
                reason,
                "success",
            )

            logger.info(
                f"Document {doc_id} updated successfully to version {new_version}"
            )
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update document {doc_id}: {e}")
            self._log_operation(
                doc_id,
                DocumentOperation.UPDATE,
                os.path.basename(new_filepath),
                existing_doc[0] if existing_doc else None,
                reason,
                "failed",
                str(e),
            )
            return False
        finally:
            cur.close()
            conn.close()

    def delete_document(
        self, doc_id: str, reason: str = None, soft_delete: bool = True
    ) -> bool:
        """
        Delete a document (soft or hard delete).

        Args:
            doc_id: Document ID to delete.
            reason: Reason for the deletion.
            soft_delete: If True, mark as inactive; if False, permanently remove (default: True).

        Returns:
            True if the deletion was successful, False otherwise.
        """
        if not settings.enable_document_deletion:
            logger.warning("Document deletion is disabled")
            return False

        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Look up existing document
            cur.execute(
                "SELECT filename, filepath FROM documents WHERE id = %s", (doc_id,)
            )
            doc_info = cur.fetchone()

            if not doc_info:
                logger.error(f"Document {doc_id} not found")
                return False

            filename, filepath = doc_info

            if soft_delete:
                # Soft delete: deactivate versions and remove chunks
                cur.execute(
                    """
                    UPDATE document_versions
                    SET is_active = FALSE
                    WHERE doc_id = %s AND is_active = TRUE
                """,
                    (doc_id,),
                )

                # Remove all chunks
                cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))

                # Reset chunk count (keep document record)
                cur.execute(
                    """
                    UPDATE documents
                    SET chunk_count = 0
                    WHERE id = %s
                """,
                    (doc_id,),
                )

                # Record delete version
                cur.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM document_versions WHERE doc_id = %s",
                    (doc_id,),
                )
                current_version = cur.fetchone()[0]
                new_version = current_version + 1

                cur.execute(
                    """
                    INSERT INTO document_versions (doc_id, version, filename, filepath, chunk_count, operation, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                """,
                    (
                        doc_id,
                        new_version,
                        filename,
                        filepath,
                        0,
                        DocumentOperation.DELETE.value,
                    ),
                )

            else:
                # Hard delete: permanently remove all records
                cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))
                cur.execute(
                    "DELETE FROM document_versions WHERE doc_id = %s", (doc_id,)
                )
                cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))

            conn.commit()
            self._remove_profile_best_effort(doc_id)

            # Log the operation
            delete_type = "soft_delete" if soft_delete else "hard_delete"
            self._log_operation(
                doc_id,
                DocumentOperation.DELETE,
                filename,
                None,
                reason,
                "success",
                f"Delete type: {delete_type}",
            )

            logger.info(
                f"Document {doc_id} {'soft' if soft_delete else 'hard'} deleted successfully"
            )
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete document {doc_id}: {e}")
            self._log_operation(
                doc_id,
                DocumentOperation.DELETE,
                doc_info[0] if doc_info else None,
                None,
                reason,
                "failed",
                str(e),
            )
            return False
        finally:
            cur.close()
            conn.close()

    def replace_document(
        self, doc_id: str, new_filepath: str, reason: str = None
    ) -> bool:
        """
        Replace a document entirely (delete old content and insert new, keeping same doc_id).

        Args:
            doc_id: Document ID to replace.
            new_filepath: Path to the replacement document file.
            reason: Reason for the replacement.

        Returns:
            True if the replacement was successful, False otherwise.
        """
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # Look up existing document
            cur.execute(
                "SELECT filename, filepath FROM documents WHERE id = %s", (doc_id,)
            )
            existing_doc = cur.fetchone()

            if not existing_doc:
                logger.error(f"Document {doc_id} not found for replacement")
                return False

            old_filename, old_filepath = existing_doc

            # Verify replacement file exists
            if not os.path.exists(new_filepath):
                logger.error(f"Replacement file not found: {new_filepath}")
                return False

            # Delete existing chunks
            cur.execute("DELETE FROM document_chunks WHERE doc_id = %s", (doc_id,))

            # Process replacement document
            try:
                new_filename = os.path.basename(new_filepath)
                documents = self.document_loader.load_document(new_filepath)
                if not documents:
                    raise ValueError(f"No content loaded from {new_filepath}")

                # Split into chunks
                chunks = []
                for doc in documents:
                    doc_chunks = self.chunker.chunk_document(doc)
                    chunks.extend([chunk.page_content for chunk in doc_chunks])

                if not chunks:
                    raise ValueError(f"No chunks generated from {new_filepath}")

                # Generate embeddings
                embeddings = [embed_single_text(chunk) for chunk in chunks]

            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to process replacement document: {e}")
                self._log_operation(
                    doc_id,
                    DocumentOperation.REPLACE,
                    new_filename,
                    old_filename,
                    reason,
                    "failed",
                    str(e),
                )
                return False

            # Insert new chunks
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    """
                    INSERT INTO document_chunks (doc_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                """,
                    (doc_id, i, chunk, embedding),
                )

            # Update document metadata
            cur.execute(
                """
                UPDATE documents
                SET filename = %s, filepath = %s, chunk_count = %s
                WHERE id = %s
            """,
                (new_filename, new_filepath, len(chunks), doc_id),
            )

            # Record new version
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM document_versions WHERE doc_id = %s",
                (doc_id,),
            )
            current_version = cur.fetchone()[0]
            new_version = current_version + 1

            cur.execute(
                """
                INSERT INTO document_versions (doc_id, version, filename, filepath, chunk_count, operation, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            """,
                (
                    doc_id,
                    new_version,
                    new_filename,
                    new_filepath,
                    len(chunks),
                    DocumentOperation.REPLACE.value,
                ),
            )

            conn.commit()
            self._refresh_profile_best_effort(doc_id)

            # Log successful operation
            self._log_operation(
                doc_id,
                DocumentOperation.REPLACE,
                new_filename,
                old_filename,
                reason,
                "success",
            )

            logger.info(
                f"Document {doc_id} replaced successfully with version {new_version}"
            )
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to replace document {doc_id}: {e}")
            self._log_operation(
                doc_id,
                DocumentOperation.REPLACE,
                os.path.basename(new_filepath),
                existing_doc[0] if existing_doc else None,
                reason,
                "failed",
                str(e),
            )
            return False
        finally:
            cur.close()
            conn.close()

    def get_document_versions(self, doc_id: str) -> List[DocumentVersion]:
        """Get all versions of a document, ordered by version descending."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT doc_id, version, filename, filepath, chunk_count, created_at, operation, is_active
                FROM document_versions
                WHERE doc_id = %s
                ORDER BY version DESC
            """,
                (doc_id,),
            )

            versions = []
            for row in cur.fetchall():
                versions.append(
                    DocumentVersion(
                        doc_id=row[0],
                        version=row[1],
                        filename=row[2],
                        filepath=row[3],
                        chunk_count=row[4],
                        created_at=row[5],
                        operation=DocumentOperation(row[6]),
                        is_active=row[7],
                    )
                )

            return versions

        except Exception as e:
            logger.error(f"Failed to get document versions for {doc_id}: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def restore_document_version(
        self, doc_id: str, version: int, reason: str = None
    ) -> bool:
        """Restore a document to a previous version."""
        # Not yet implemented
        # Future: reload the specified version's content and re-embed
        logger.info(
            f"Document version restoration not yet implemented for {doc_id} version {version}"
        )
        return False

    def get_operation_log(self, doc_id: str = None, limit: int = 50) -> List[Dict]:
        """Get the document operations log, optionally filtered by doc_id."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            if doc_id:
                cur.execute(
                    """
                    SELECT doc_id, operation, filename, old_filename, reason, status, error_message, created_at
                    FROM document_operations_log
                    WHERE doc_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """,
                    (doc_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT doc_id, operation, filename, old_filename, reason, status, error_message, created_at
                    FROM document_operations_log
                    ORDER BY created_at DESC
                    LIMIT %s
                """,
                    (limit,),
                )

            logs = []
            for row in cur.fetchall():
                logs.append(
                    {
                        "doc_id": row[0],
                        "operation": row[1],
                        "filename": row[2],
                        "old_filename": row[3],
                        "reason": row[4],
                        "status": row[5],
                        "error_message": row[6],
                        "created_at": row[7],
                    }
                )

            return logs

        except Exception as e:
            logger.error(f"Failed to get operation log: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def _log_operation(
        self,
        doc_id: str,
        operation: DocumentOperation,
        filename: str,
        old_filename: str = None,
        reason: str = None,
        status: str = "success",
        error_message: str = None,
    ):
        """Record a document operation in the operations log."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO document_operations_log
                (doc_id, operation, filename, old_filename, reason, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    doc_id,
                    operation.value,
                    filename,
                    old_filename,
                    reason,
                    status,
                    error_message,
                ),
            )
            conn.commit()

        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
        finally:
            cur.close()
            conn.close()

    def get_document_statistics(self) -> Dict:
        """Get aggregate document statistics."""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            stats = {}

            # Total document count
            cur.execute("SELECT COUNT(*) FROM documents")
            stats["total_documents"] = cur.fetchone()[0]

            # Active document count
            cur.execute(
                """
                SELECT COUNT(DISTINCT dv.doc_id)
                FROM document_versions dv
                WHERE dv.is_active = TRUE
            """
            )
            stats["active_documents"] = cur.fetchone()[0]

            # Total chunk count
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            stats["total_chunks"] = cur.fetchone()[0]

            # Operation breakdown
            cur.execute(
                """
                SELECT operation, COUNT(*)
                FROM document_versions
                GROUP BY operation
            """
            )
            operation_stats = dict(cur.fetchall())
            stats["operations"] = operation_stats

            return stats

        except Exception as e:
            logger.error(f"Failed to get document statistics: {e}")
            return {}
        finally:
            cur.close()
            conn.close()
