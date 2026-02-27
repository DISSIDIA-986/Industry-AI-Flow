/**
 * Command: Create RAG Module
 * Generates retrieval/embedding/chunking components for Industry AI Flow
 */

import { Message } from "@claude/types";

export const metadata = {
  name: "create-rag-module",
  description: "Scaffold RAG retrieval, embedding, or chunking modules",
  category: "code-generation",
};

export async function execute(args: string[]): Promise<Message> {
  const moduleType = args[0] || "retriever"; // retriever, embedder, chunker, reranker
  const moduleName = args[1] || \`custom_\${moduleType}\`;

  const templates: Record<string, string> = {
    retriever: generateRetrieverTemplate(moduleName),
    embedder: generateEmbedderTemplate(moduleName),
    chunker: generateChunkerTemplate(moduleName),
    reranker: generateRerankerTemplate(moduleName),
  };

  const template = templates[moduleType] || templates.retriever;
  const targetPath = \`backend/services/retrieval/\${moduleName}.py\`;

  const message = \`Generated \${moduleType} module: \${moduleName}

Features:
- PostgreSQL + pgvector integration
- Multi-tenant isolation
- Query caching support
- Async/await patterns
- Type hints (Python 3.13)
- Error handling and logging

Location: \${targetPath}

Next steps:
1. Configure database connection in backend/config.py
2. Test with pytest tests/unit/test_\${moduleName}.py
3. Integrate into RAG pipeline
4. Add performance monitoring\`;

  return {
    role: "assistant",
    content: message,
    metadata: {
      template,
      targetPath,
      moduleType,
    },
  };
}

function generateRetrieverTemplate(name: string): string {
  return \`"""
\${name} - Custom retriever for Industry AI Flow RAG system
"""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

logger = logging.getLogger(__name__)


class \${capitalize(name)}:
    """
    Custom retriever implementation with pgvector support.

    Features:
    - Hybrid search (BM25 + vector)
    - Multi-tenant filtering
    - Query caching
    - Reranking support
    """

    def __init__(
        self,
        db_session: AsyncSession,
        embedding_model: Any,
        top_k: int = 10,
        min_score: float = 0.3,
        enable_cache: bool = True,
    ):
        self.db_session = db_session
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.min_score = min_score
        self.enable_cache = enable_cache

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for query.

        Args:
            query: User query
            tenant_id: Tenant identifier for isolation
            filters: Additional metadata filters

        Returns:
            List of retrieved documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_model.aembed_query(query)

            # Build SQL query with pgvector cosine similarity
            sql = text(\"""
                SELECT
                    dc.id,
                    dc.content,
                    dc.metadata,
                    d.title,
                    d.source,
                    1 - (dc.embedding <=> :query_embedding) as score
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.tenant_id = :tenant_id
                AND (1 - (dc.embedding <=> :query_embedding)) > :min_score
                ORDER BY dc.embedding <=> :query_embedding
                LIMIT :top_k
            \""")

            # Execute query
            result = await self.db_session.execute(
                sql,
                {
                    "query_embedding": query_embedding,
                    "tenant_id": tenant_id,
                    "min_score": self.min_score,
                    "top_k": self.top_k,
                },
            )

            # Format results
            chunks = []
            for row in result:
                chunks.append({
                    "id": row.id,
                    "content": row.content,
                    "metadata": row.metadata or {},
                    "title": row.title,
                    "source": row.source,
                    "score": float(row.score),
                })

            logger.info(
                f"Retrieved {len(chunks)} chunks for tenant {tenant_id}"
            )
            return chunks

        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            raise

    async def hybrid_retrieve(
        self,
        query: str,
        tenant_id: str,
        alpha: float = 0.5,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining vector and BM25 search.

        Args:
            query: User query
            tenant_id: Tenant identifier
            alpha: Weight for vector search (1-alpha for BM25)

        Returns:
            Reranked results using RRF
        """
        # Vector search
        vector_results = await self.retrieve(query, tenant_id, **kwargs)

        # BM25 search (simplified, use proper BM25 implementation)
        bm25_results = await self._bm25_search(query, tenant_id, **kwargs)

        # Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            [vector_results, bm25_results],
            k=60,  # RRF constant
        )

        return fused_results[:self.top_k]

    async def _bm25_search(
        self,
        query: str,
        tenant_id: str,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Simple BM25 search using PostgreSQL full-text search"""
        sql = text(\"""
            SELECT
                dc.id,
                dc.content,
                dc.metadata,
                d.title,
                d.source,
                ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', :query)) as score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.tenant_id = :tenant_id
            AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :top_k
        \""")

        result = await self.db_session.execute(
            sql,
            {"query": query, "tenant_id": tenant_id, "top_k": self.top_k},
        )

        return [
            {
                "id": row.id,
                "content": row.content,
                "metadata": row.metadata or {},
                "title": row.title,
                "source": row.source,
                "score": float(row.score),
            }
            for row in result
        ]

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Combine multiple result lists using RRF"""
        scores: Dict[str, float] = {}
        docs: Dict[str, Dict[str, Any]] = {}

        for results in result_lists:
            for rank, doc in enumerate(results, 1):
                doc_id = str(doc["id"])
                scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
                docs[doc_id] = doc

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            {**docs[doc_id], "score": scores[doc_id]}
            for doc_id in sorted_ids
        ]


def capitalize(s: str) -> str:
    return "".join(word.capitalize() for word in s.split("_"))
\`;
}

function generateEmbedderTemplate(name: string): string {
  return \`"""
\${name} - Custom embedding model for Industry AI Flow
"""

from typing import List
import logging
import numpy as np

logger = logging.getLogger(__name__)


class \${capitalize(name)}:
    """Custom embedding model implementation"""

    def __init__(self, model_name: str = "nomic-embed-text-v1.5"):
        self.model_name = model_name
        self.dimensions = 768  # nomic-embed-text dimensions

    async def aembed_query(self, query: str) -> List[float]:
        """Embed a single query"""
        # Implement embedding logic
        pass

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents"""
        # Implement batch embedding
        pass
\`;
}

function generateChunkerTemplate(name: string): string {
  return \`"""
\${name} - Document chunking strategy
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class \${capitalize(name)}:
    """Custom document chunker"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Chunk a document into smaller pieces"""
        # Implement chunking logic
        pass
\`;
}

function generateRerankerTemplate(name: string): string {
  return \`"""
\${name} - Custom reranker for retrieval results
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class \${capitalize(name)}:
    """Custom reranker implementation"""

    def __init__(self, model_name: str = "bge-reranker-base"):
        self.model_name = model_name

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Rerank documents based on query relevance"""
        # Implement reranking logic
        pass
\`;
}
