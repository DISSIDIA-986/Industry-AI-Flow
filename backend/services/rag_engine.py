from backend.services.core.embedder import embed_single_text
from backend.services.core.vectorstore import VectorStore
from backend.services.llm_integration.llm_client import get_llm_client, get_backend_status
from backend.services.retrieval.hybrid_search import HybridRetriever
from backend.services.retrieval.reranker import Reranker
from backend.services.feedback_system.feedback_manager import FeedbackManager, UserFeedback, FeedbackType
from backend.config import settings
import uuid
import datetime
import logging
import time

logger = logging.getLogger(__name__)


class SimpleRAG:
    def __init__(self, use_hybrid_search: bool = True, use_reranker: bool = True, enable_feedback: bool = True):
        """
        初始化 RAG 系统

        Args:
            use_hybrid_search: 是否使用混合检索（BM25 + 向量）
            use_reranker: 是否使用重排序模块
            enable_feedback: 是否启用反馈机制
        """
        self.vectorstore = VectorStore()
        self.llm_client = get_llm_client()  # 使用工厂方法获取客户端
        self.use_hybrid_search = use_hybrid_search
        self.use_reranker = use_reranker
        self.enable_feedback = enable_feedback

        # 记录后端信息
        backend_status = get_backend_status()
        logger.info(f"✅ RAG 引擎初始化完成 - 后端: {backend_status.get('backend', 'unknown')}")

        # Phase 2 Step 2: 初始化混合检索器
        if use_hybrid_search:
            self.hybrid_retriever = HybridRetriever(self.vectorstore)
        else:
            self.hybrid_retriever = None

        # Phase 2 Step 3: 初始化重排序器
        if use_reranker:
            self.reranker = Reranker()
        else:
            self.reranker = None

        # 初始化反馈管理器
        if enable_feedback:
            self.feedback_manager = FeedbackManager(self.vectorstore, self.reranker)
        else:
            self.feedback_manager = None

    def query(self, question: str, top_k: int = None, temperature: float = None, max_tokens: int = None) -> dict:
        """RAG查询流程"""
        if top_k is None:
            top_k = settings.top_k

        # 生成查询ID用于反馈跟踪
        query_id = str(uuid.uuid4())

        # 获取自适应搜索权重（如果启用反馈）
        vector_weight, bm25_weight = self._get_adaptive_search_weights()

        # Phase 2 Step 2: 使用混合检索或纯向量检索
        if self.use_hybrid_search and self.hybrid_retriever:
            # 混合检索（BM25 + 向量），先获取更多候选（top_k * 2）
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            similar_chunks = self.hybrid_retriever.search(
                query=question, top_k=retrieve_k, vector_weight=vector_weight, bm25_weight=bm25_weight
            )
        else:
            # 纯向量检索（Phase 1 方法）
            retrieve_k = top_k * 2 if self.use_reranker else top_k
            query_embedding = embed_single_text(question)
            similar_chunks = self.vectorstore.similarity_search(query_embedding, top_k=retrieve_k)

        # Phase 2 Step 3: 使用重排序器精排
        if self.use_reranker and self.reranker and similar_chunks:
            similar_chunks = self.reranker.rerank(
                query=question, documents=similar_chunks, top_k=top_k
            )

        # 3. 构建提示词
        # 为每个文档块添加编号，提高可读性
        context_parts = []
        for i, chunk in enumerate(similar_chunks, 1):
            context_parts.append(f"[文档{i}]\n{chunk['content']}")
        context = "\n\n".join(context_parts)

        prompt = self._build_prompt(question, context)

        # 4. LLM生成答案
        answer = self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)

        # 5. 返回结果
        return {
            "query_id": query_id,
            "question": question,
            "answer": answer,
            "sources": [chunk['doc_id'] for chunk in similar_chunks],
            "retrieved_chunks": similar_chunks,
            "search_weights": {"vector_weight": vector_weight, "bm25_weight": bm25_weight}
        }

    def _get_adaptive_search_weights(self) -> tuple:
        """获取自适应搜索权重"""
        if not self.feedback_manager:
            return 0.7, 0.3  # 默认权重

        try:
            # 获取最近的反馈统计
            stats = self.feedback_manager.get_feedback_statistics(days=1)
            if stats.total_queries >= 5:  # 至少有5个反馈才调整
                if stats.success_rate < 0.5:
                    # 成功率低，增加向量搜索权重
                    return 0.8, 0.2
                elif stats.success_rate > 0.8:
                    # 成功率高，略微增加关键词权重
                    return 0.6, 0.4
        except Exception as e:
            logger.warning(f"Failed to get adaptive search weights: {e}")

        return 0.7, 0.3  # 默认权重

    def _build_prompt(self, question: str, context: str) -> str:
        """构建提示词"""
        return f"""你是一个专业的技术问答助手。请基于以下参考文档回答用户问题。

**重要指示**：
1. 仔细阅读所有参考文档
2. 只使用文档中的信息回答
3. 如果文档中没有相关信息，明确说"我不知道"
4. 回答要准确、简洁、专业

**参考文档**：
{context}

**用户问题**：{question}

**你的回答**："""

    def submit_feedback(self, query_id: str, question: str, answer: str, feedback_type: str,
                       user_comment: str = None, retrieved_chunks: list = None, feedback_weight: float = 1.0) -> bool:
        """提交用户反馈"""
        if not self.feedback_manager:
            logger.warning("Feedback system is not enabled")
            return False

        try:
            feedback_enum = FeedbackType(feedback_type.lower())
            feedback = UserFeedback(
                query_id=query_id,
                question=question,
                answer=answer,
                feedback_type=feedback_enum,
                user_comment=user_comment,
                retrieved_chunks=retrieved_chunks or [],
                feedback_weight=feedback_weight
            )
            return self.feedback_manager.record_feedback(feedback)
        except ValueError:
            logger.error(f"Invalid feedback type: {feedback_type}")
            return False
        except Exception as e:
            logger.error(f"Failed to submit feedback: {e}")
            return False

    def get_feedback_statistics(self, days: int = 7) -> dict:
        """获取反馈统计信息"""
        if not self.feedback_manager:
            return {"message": "Feedback system is not enabled"}

        try:
            stats = self.feedback_manager.get_feedback_statistics(days)
            return {
                "total_queries": stats.total_queries,
                "helpful_count": stats.helpful_count,
                "not_helpful_count": stats.not_helpful_count,
                "partially_helpful_count": stats.partially_helpful_count,
                "success_rate": stats.success_rate,
                "avg_feedback_weight": stats.avg_feedback_weight
            }
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {"error": str(e)}

    def get_high_quality_documents(self, min_score: float = 0.5, limit: int = 100) -> list:
        """获取高质量文档列表"""
        if not self.feedback_manager:
            return []

        try:
            return self.feedback_manager.get_high_quality_documents(min_score, limit)
        except Exception as e:
            logger.error(f"Failed to get high quality documents: {e}")
            return []

    def add_documents(self, documents: list) -> bool:
        """
        添加文档到RAG系统

        Args:
            documents: 文档列表,每个文档包含content和metadata

        Returns:
            bool: 是否成功
        """
        try:
            from backend.services.core.chunker import chunk_text
            from backend.services.core.embedder import embed_texts

            # 分块
            all_chunks = []

            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                doc_id = metadata.get('doc_id', str(uuid.uuid4()))

                # Use the standalone chunk_text function
                chunk_dicts = chunk_text(content, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
                for i, chunk_dict in enumerate(chunk_dicts):
                    all_chunks.append({
                        'doc_id': doc_id,
                        'chunk_id': f"{doc_id}_chunk_{i}",
                        'content': chunk_dict['content'],
                        'metadata': metadata
                    })

            # 向量化并存储
            texts = [chunk['content'] for chunk in all_chunks]
            embeddings = embed_texts(texts)

            # Store documents using store_document_with_chunks
            # Group by doc_id for proper storage
            doc_groups = {}
            for chunk, embedding in zip(all_chunks, embeddings):
                doc_id = chunk['doc_id']
                if doc_id not in doc_groups:
                    doc_groups[doc_id] = {'chunks': [], 'embeddings': [], 'metadata': chunk['metadata']}
                doc_groups[doc_id]['chunks'].append(chunk['content'])
                doc_groups[doc_id]['embeddings'].append(embedding)

            # Store each document
            for doc_id, data in doc_groups.items():
                metadata = data['metadata']
                filename = metadata.get('source', doc_id)
                filepath = metadata.get('source', doc_id)
                self.vectorstore.store_document_with_chunks(
                    filename=filename,
                    filepath=filepath,
                    chunks=data['chunks'],
                    embeddings=data['embeddings']
                )

            logger.info(f"Successfully added {len(documents)} documents with {len(all_chunks)} chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档ID

        Returns:
            bool: 是否成功
        """
        try:
            # 删除文档的所有chunks
            self.vectorstore.delete_by_doc_id(doc_id)
            logger.info(f"Successfully deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
