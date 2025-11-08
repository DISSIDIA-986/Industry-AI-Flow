# LangChain 1.0 升级计划 (增强版)

## 项目背景

当前项目是基于自定义实现的RAG系统，使用了原生的PostgreSQL/pgvector、sentence-transformers、requests以及自定义的RAG逻辑。升级到LangChain 1.0将带来标准化的组件和更简洁的开发模式。

## 当前状态分析

- **LLM客户端**: 自定义Ollama客户端使用requests库
- **向量化**: 使用sentence-transformers库
- **向量存储**: 自定义PostgreSQL/pgvector操作
- **检索**: 自定义混合检索（BM25 + 向量）
- **重排序**: 使用HuggingFace transformers模型
- **RAG引擎**: 自定义RAG逻辑
- **元数据功能**: 提案阶段（见 METADATA_RETRIEVAL_PROPOSAL.md），当前系统不支持元数据过滤

## 升级目标

1. 将现有自定义组件替换为LangChain 1.0标准组件
2. 简化RAG流程代码
3. 提高可维护性和扩展性
4. 保持现有功能特性（混合检索、重排序等）
5. 确保性能不低于当前水平
6. 集成LangSmith进行调试和可观测性
7. **新增**: 为未来元数据过滤功能预留架构支持

## 迁移策略：渐进式迁移 (核心策略)

为降低风险，避免"大爆炸式"迁移，采用渐进式迁移策略。每次仅替换一个核心组件，进行充分的验证和基准测试后，再进行下一步迁移。

## 迁移计划

### 第一阶段：环境准备与基础设置

1. **更新依赖**: 在`requirements.txt`中添加LangChain 1.0相关包
2. **配置LangSmith**: 配置环境变量以启用LangSmith追踪
3. **建立基准测试套件**: 为现有系统建立性能基准，记录当前的延迟、吞吐量、准确率等指标
4. **数据库架构规划**: 考虑未来可能的元数据字段扩展

```txt
langchain==0.1.0  # 或最新稳定版
langchain-community==0.0.0  # 社区组件
langchain-core==0.1.0  # 核心库
langchain-ollama==0.0.0  # Ollama集成
langchain-pg==0.0.0  # PostgreSQL/pgvector集成
langchain-elasticsearch==0.0.0  # 用于BM25检索（如果需要）
```

**LangSmith配置**:
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
export LANGSMITH_API_KEY="your-api-key"
export LANGSMITH_PROJECT="migration-phase-1"  # 用于区分不同阶段
```

### 第二阶段：LLM客户端迁移 (Step 1)

**目标**: 仅替换Ollama客户端，保持其他组件不变

**实现**:
```python
from langchain_ollama import ChatOllama

# 创建新的LangChain Ollama客户端
llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_host,
    temperature=0
)

# 保持原有的RAG逻辑不变，仅替换llm生成部分
# 使用LangSmith追踪
llm = llm.with_config(run_name="new_ollama_client")
```

**验证**:
- 对比新旧客户端生成的文本质量
- 测试延迟和吞吐量
- 确保API响应格式兼容

### 第三阶段：向量化组件迁移 (Step 2)

**目标**: 在第二阶段成功的基础上，替换向量化组件

**实现**:
```python
from langchain_ollama import OllamaEmbeddings

# 或使用HuggingFace模型
from langchain.embeddings import HuggingFaceEmbeddings

embeddings = OllamaEmbeddings(
    model=settings.embedding_model,
    base_url=settings.ollama_host
)

# 或使用HuggingFace模型（适用于nomic-embed-text-v1.5）
embeddings = HuggingFaceEmbeddings(
    model_name=settings.embedding_model,
    model_kwargs={'trust_remote_code': True}  # 适用于nomic-embed-text-v1.5
)
```

**验证**:
- 对比新旧向量化组件生成的向量一致性
- 测试向量化性能
- 验证与现有数据库的兼容性

### 第四阶段：向量存储迁移 (Step 3) - **增强以支持未来元数据过滤**

**目标**: 在前两个阶段成功的基础上，替换向量存储组件，**增强以支持未来元数据过滤**

**实现**:
```python
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from sqlalchemy import create_engine
from langchain_core.documents import Document
import json

# 增强版向量存储，支持元数据过滤
class EnhancedPGVector(PGVector):
    """
    扩展PGVector以支持更复杂的元数据过滤功能
    预留接口以支持未来METADATA_RETRIEVAL_PROPOSAL.md中的功能
    """

    def similarity_search_with_filter(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        doc_ids: list[str] = None,  # 通过文档ID过滤
        metadata_filters: dict = None  # 通过元数据字段过滤
    ) -> list[Document]:
        """
        带过滤的相似度搜索

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            doc_ids: 预过滤的文档ID列表（None表示不过滤）
            metadata_filters: 元数据过滤条件（None表示不过滤）
        """
        # 构建基础SQL
        base_sql = """
            SELECT
                dc.doc_id,
                dc.id as chunk_id,
                dc.content,
                dc.embedding <=> %s::vector AS distance,
                d.filename,
                d.metadata as doc_metadata  -- 包含完整元数据
            FROM document_chunks dc
            JOIN documents d ON dc.doc_id = d.id
        """

        # 构建WHERE子句
        where_clauses = ["1=1"]
        params = [query_embedding.tolist()]  # 确保向量参数正确传递，由驱动处理格式化

        # 文档ID过滤 - 使用参数化数组
        if doc_ids:
            where_clauses.append("dc.doc_id = ANY(%s)")
            params.append(doc_ids)  # 传递数组作为单个参数

        # 元数据过滤（预留接口）
        if metadata_filters:
            # 解析元数据过滤条件
            filters_sql, filters_params = self._build_metadata_filter(metadata_filters)
            where_clauses.extend(filters_sql)
            params.extend(filters_params)

        # 完整SQL - 避免f-string拼接
        where_sql = ' AND '.join(where_clauses)
        full_sql = base_sql + " WHERE " + where_sql + " ORDER BY distance LIMIT %s"
        params.append(top_k)

        # 执行查询（使用上下文管理器确保资源正确释放）
        try:
            with self.connection.cursor() as cur:
                cur.execute(full_sql, params)
                results = []

                for row in cur.fetchall():
                    metadata = {
                        'doc_id': row[0],
                        'chunk_id': row[1],
                        'distance': float(row[3]),
                        'filename': row[4],
                        'document_metadata': row[5]  # 包含完整文档元数据
                    }

                    # 添加元数据过滤信息
                    if metadata_filters:
                        metadata['filtered_by'] = metadata_filters

                    doc = Document(
                        page_content=row[2],  # content
                        metadata=metadata
                    )
                    results.append(doc)

                return results
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise  # 重新抛出异常，不静默处理

    def _build_metadata_filter(self, filters: dict) -> tuple[list[str], list]:
        """
        构建元数据过滤SQL子句
        对应 METADATA_RETRIEVAL_PROPOSAL.md 中的过滤功能
        """
        where_clauses = []
        params = []

        # 文档类型过滤
        if "document_type" in filters:
            where_clauses.append("d.document_type = %s")
            params.append(filters["document_type"])

        # 日期范围过滤
        if "date_range" in filters:
            if "start" in filters["date_range"]:
                where_clauses.append("d.created_date >= %s")
                params.append(filters["date_range"]["start"])
            if "end" in filters["date_range"]:
                where_clauses.append("d.created_date <= %s")
                params.append(filters["date_range"]["end"])

        # 部门过滤
        if "department" in filters:
            where_clauses.append("d.department = %s")
            params.append(filters["department"])

        # 标签过滤（包含任一标签）
        if "tags" in filters and filters["tags"]:
            where_clauses.append("d.tags && %s")  # PostgreSQL 数组overlap操作符
            params.append(filters["tags"])

        # 安全级别过滤
        if "security_level" in filters:
            where_clauses.append("d.security_level = %s")
            params.append(filters["security_level"])

        # JSONB元数据过滤
        if "custom_fields" in filters:
            for field, value in filters["custom_fields"].items():
                where_clauses.append(f"d.metadata->>%s = %s")
                params.extend([field, json.dumps(value) if isinstance(value, (dict, list)) else str(value)])

        return where_clauses, params

# 建立连接
connection_string = settings.database_url
collection_name = "document_chunks"

# 创建增强版LangChain PGVector实例
vectorstore = EnhancedPGVector(
    connection=connection_string,
    embedding_function=embeddings,
    collection_name=collection_name,
    use_jsonb=True  # 支持JSONB元数据存储
)

# 渐进式测试：同时使用新旧向量存储进行查询对比
def validate_vectorstore_consistency(query_embedding):
    # 旧版查询
    old_results = old_vectorstore.similarity_search(query_embedding, top_k=5)
    # 新版查询
    new_results = vectorstore.similarity_search_with_filter(query_embedding, top_k=5)
    # 对比结果
    return compare_results(old_results, new_results)
```

**验证**:
- 检查检索结果的一致性
- 比较查询性能
- 验证数据完整性
- 测试元数据过滤预留功能（即使当前不使用）

### 第五阶段：混合检索逻辑迁移 (Step 4) - **增强以支持未来元数据过滤**

**目标**: 实现LangChain版本的混合检索，保持BM25 + 向量的功能，**并预留元数据过滤接口**

**实现**:
```python
from langchain.retrievers import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from typing import List, Optional
from langchain.schema import Document, BaseRetriever
import json

class EnhancedHybridRetriever(BaseRetriever):
    """
    增强版混合检索器，支持元数据过滤
    对应 METADATA_RETRIEVAL_PROPOSAL.md 中的 hybrid search with metadata filters
    """
    vectorstore: EnhancedPGVector  # 使用增强版向量存储
    k: int = 5
    vector_weight: float = 0.7
    bm25_weight: float = 0.3

    def __init__(
        self,
        vectorstore: EnhancedPGVector,
        k: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ):
        super().__init__()
        self.vectorstore = vectorstore
        self.k = k
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def _get_relevant_documents(
        self,
        query: str,
        *,
        filters: dict = None,  # 元数据过滤参数
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        """
        获取相关文档（支持元数据过滤）

        Args:
            query: 查询文本
            filters: 元数据过滤条件
            run_manager: 回调管理器
        """
        # 从PostgreSQL获取文档用于BM25分词
        # 为简化实现，这里使用PostgreSQL的内置全文搜索功能
        # 实际实现可能需要更复杂的集成

        # 应用元数据过滤（获取符合条件的文档ID）
        filtered_doc_ids = None
        if filters:
            # 使用向量存储的元数据过滤功能
            # 注意：这里我们预留了接口，实际实现可能需要更复杂的方法
            # 临时实现：通过向量查询执行元数据过滤
            filtered_doc_ids = self._get_filtered_doc_ids(filters)

        # 1. 向量检索（使用过滤后的文档ID）
        query_embedding = self.vectorstore.embedding_function.embed_query(query)
        vector_results = self.vectorstore.similarity_search_with_filter(
            query_embedding,
            top_k=self.k * 2,
            doc_ids=filtered_doc_ids
        )

        # 2. BM25检索（使用过滤后的文档）
        # 由于LangChain的BM25实现需要文档内容，我们需要从数据库获取过滤后的文档
        bm25_results = self._bm25_search(query, filtered_doc_ids, top_k=self.k * 2)

        # 3. 融合得分 (Reciprocal Rank Fusion - RRF)
        fused_scores = {}

        # 向量检索结果加权（使用倒数排名）
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.metadata.get("chunk_id") or result.metadata.get("doc_id")
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + self.vector_weight / rank

        # BM25检索结果加权
        for rank, (chunk_id, score) in enumerate(bm25_results, 1):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + self.bm25_weight / rank

        # 4. 排序并返回 top_k 结果
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:self.k]

        # 5. 构建最终结果（仅返回最高分的文档）
        final_results = []
        chunk_id_to_doc = {doc.metadata.get("chunk_id") or doc.metadata.get("doc_id"): doc for doc in vector_results}

        for chunk_id, fusion_score in sorted_chunks:
            if chunk_id in chunk_id_to_doc:
                doc = chunk_id_to_doc[chunk_id]
                # 添加融合分数到元数据
                doc.metadata["fusion_score"] = fusion_score
                final_results.append(doc)

        return final_results

    def _get_filtered_doc_ids(self, filters: dict) -> List[str]:
        """
        根据过滤条件获取文档ID列表
        """
        # 这里应该查询数据库获取符合条件的文档ID
        # 由于PostgreSQL支持复杂的查询，直接在数据库层面过滤会更高效
        # 为了与METADATA_RETRIEVAL_PROPOSAL.md保持一致，我们构建SQL查询

        conn = self.vectorstore.connection

        try:
            with conn.cursor() as cur:
                where_clauses = []
                params = []

                # 文档类型过滤
                if "document_type" in filters:
                    where_clauses.append("document_type = %s")
                    params.append(filters["document_type"])

                # 日期范围过滤
                if "date_range" in filters:
                    if "start" in filters["date_range"]:
                        where_clauses.append("created_date >= %s")
                        params.append(filters["date_range"]["start"])
                    if "end" in filters["date_range"]:
                        where_clauses.append("created_date <= %s")
                        params.append(filters["date_range"]["end"])

                # 部门过滤
                if "department" in filters:
                    where_clauses.append("department = %s")
                    params.append(filters["department"])

                # 标签过滤（包含任一标签）
                if "tags" in filters and filters["tags"]:
                    where_clauses.append("tags && %s")  # PostgreSQL 数组overlap操作符
                    params.append(filters["tags"])

                # 安全级别过滤
                if "security_level" in filters:
                    where_clauses.append("security_level = %s")
                    params.append(filters["security_level"])

                # 自定义字段过滤（JSONB）
                if "custom_fields" in filters:
                    for field, value in filters["custom_fields"].items():
                        where_clauses.append("metadata->>%s = %s")
                        params.extend([field, json.dumps(value) if isinstance(value, (dict, list)) else str(value)])

                # 构建SQL
                if not where_clauses:
                    return None  # 无过滤条件

                where_sql = " AND ".join(where_clauses)
                sql = "SELECT id FROM documents WHERE " + where_sql

                cur.execute(sql, tuple(params))
                doc_ids = [row[0] for row in cur.fetchall()]

                print(f"📌 元数据过滤: {len(doc_ids)} 个文档符合条件")
                return doc_ids
        except Exception as e:
            logger.error(f"Metadata filtering failed: {e}")
            raise

    def _bm25_search(self, query: str, doc_ids: Optional[List[str]], top_k: int) -> List[tuple]:
        """
        BM25检索（使用PostgreSQL全文搜索，支持中英文）

        注意：需要先创建tsvector索引：
        CREATE EXTENSION IF NOT EXISTS zhparser;
        CREATE TEXT SEARCH CONFIGURATION chinesecfg (PARSER = zhparser);
        ALTER TEXT SEARCH CONFIG chinesecfg ADD MAPPING FOR n,v,a,i,e,l,t,r,w,m WITH simple;
        CREATE INDEX idx_chunks_fts_cn ON document_chunks USING GIN(to_tsvector('chinesecfg', COALESCE(content, '')));
        """
        conn = self.vectorstore.connection

        try:
            with conn.cursor() as cur:
                where_clauses = ["to_tsvector('chinesecfg', COALESCE(dc.content, '')) @@ plainto_tsquery('chinesecfg', %s)"]
                params = [query]

                if doc_ids:
                    where_clauses.append("dc.doc_id = ANY(%s)")
                    params.append(doc_ids)

                sql = """
                    SELECT
                        dc.id as chunk_id,
                        ts_rank_cd(
                            to_tsvector('chinesecfg', COALESCE(dc.content, '')),
                            plainto_tsquery('chinesecfg', %s),
                            32
                        ) AS bm25_score
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.id
                    WHERE """ + " AND ".join(where_clauses) + """
                    ORDER BY bm25_score DESC
                    LIMIT %s
                """

                full_params = [query] + params + [top_k]
                cur.execute(sql, full_params)
                results = [(row[0], float(row[1])) for row in cur.fetchall()]
                return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            raise

    async def _aget_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        return self._get_relevant_documents(query, **kwargs)

    def search(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[dict] = None,  # 元数据过滤
        vector_weight: float = None,
        bm25_weight: float = None
    ) -> List[dict]:
        """
        兼容性接口，对应METADATA_RETRIEVAL_PROPOSAL.md中的search方法
        """
        if top_k is None:
            top_k = self.k
        if vector_weight is None:
            vector_weight = self.vector_weight
        if bm25_weight is None:
            bm25_weight = self.bm25_weight

        # 创建临时增强检索器以支持参数覆盖
        temp_retriever = EnhancedHybridRetriever(
            vectorstore=self.vectorstore,
            k=top_k,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight
        )

        # 执行检索
        docs = temp_retriever.get_relevant_documents(query, filters=filters)

        # 转换为METADATA_RETRIEVAL_PROPOSAL.md中定义的格式
        results = []
        for doc in docs:
            results.append({
                "doc_id": doc.metadata.get("doc_id"),
                "content": doc.page_content,
                "filename": doc.metadata.get("filename"),
                "score": doc.metadata.get("fusion_score", 0.0),
                "metadata": doc.metadata.get("document_metadata", {})
            })

        return results
```

**验证**:
- 检查检索结果的一致性
- 对比BM25和向量检索的平衡性
- 验证性能是否符合预期
- 测试元数据过滤预留接口

### 第六阶段：重排序功能迁移 (Step 5)

**目标**: 使用LangChain兼容的方式实现重排序功能，保持本地化特性

**实现**:
```python
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers import ContextualCompressionRetriever
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
import torch

class CrossEncoderReranker(BaseDocumentCompressor):
    """
    本地交叉编码器重排序器，保持与现有模型兼容
    增强以支持未来元数据过滤
    """
    model_name: str = "BAAI/bge-reranker-base"
    top_k: int = 5

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", top_k: int = 5):
        super().__init__()
        self.model_name = model_name
        self.top_k = top_k
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

        # 使用MPS (Apple Silicon) 或 CPU
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        self.model.to(self.device)

    def compress_documents(self, documents, query, **kwargs):
        """
        重排序文档列表
        """
        if not documents:
            return []

        # 准备输入对 [(query, doc_content), ...]
        pairs = [[query, doc.page_content] for doc in documents]

        # Tokenize
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            ).to(self.device)

            # 计算相关性分数
            scores = self.model(**inputs, return_dict=True).logits.view(-1).float()
            scores = scores.cpu().numpy()

        # 将分数和原始文档关联
        docs_with_scores = [(doc, float(score)) for doc, score in zip(documents, scores)]

        # 按分数降序排序
        reranked_docs = sorted(docs_with_scores, key=lambda x: x[1], reverse=True)

        # 返回前top_k个文档，添加分数到元数据
        result = []
        for doc, score in reranked_docs[:self.top_k]:
            # 创建新文档并添加重排序分数
            new_doc = Document(
                page_content=doc.page_content,
                metadata=doc.metadata.copy()
            )
            new_doc.metadata['rerank_score'] = score
            result.append(new_doc)

        return result

# 创建重排序检索器
reranker = CrossEncoderReranker(top_k=settings.top_k)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=hybrid_retriever  # 这里hybrid_retriever是EnhancedHybridRetriever实例
)
```

**验证**:
- 检查重排序结果质量
- 验证性能（重排序时间开销）
- 对比与原实现的准确性

### 第七阶段：RAG引擎重构 (Step 6) - **增强以支持未来元数据过滤**

**目标**: 使用LangChain框架重构完整的RAG引擎，**支持元数据过滤参数**

**实现**:
```python
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableConfig
from langchain_core.output_parsers import StrOutputParser
import uuid

class LangChainRAG:
    def __init__(self, llm, retriever, settings, use_langsmith=True):
        self.llm = llm
        self.retriever = retriever  # EnhancedHybridRetriever with metadata filtering support
        self.settings = settings  # 保存settings用于后续使用

        # 定义并保存RAG提示词模板
        template = """你是一个专业的技术问答助手。请基于以下参考文档回答用户问题。

**重要指示**：
1. 仔细阅读所有参考文档
2. 只使用文档中的信息回答
3. 如果文档中没有相关信息，明确说"我不知道"
4. 回答要准确、简洁、专业

**参考文档**：
{context}

**用户问题**：{question}

**你的回答**："""

        self.prompt = PromptTemplate.from_template(template)

        # 创建RAG链并启用LangSmith追踪
        # 注意：这仍然是基本链，高级功能（如元数据过滤）通过方法参数处理
        self.rag_chain = (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough()
            }
            | self.prompt
            | llm
            | StrOutputParser()
        )

        # 如果启用LangSmith，添加追踪配置
        if use_langsmith:
            self.rag_chain = self.rag_chain.with_config(
                run_name="final-rag-chain"
            )

    def _format_docs(self, docs):
        """格式化文档用于提示词"""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content
            context_parts.append(f"[文档{i}]\n{content}")
        return "\n\n".join(context_parts)

    def query(
        self,
        question: str,
        top_k: int = None,
        filters: dict = None  # 元数据过滤参数，对应METADATA_RETRIEVAL_PROPOSAL.md
    ) -> dict:
        """
        执行RAG查询（支持元数据过滤）

        Args:
            question: 用户问题
            top_k: 返回结果数量
            filters: 元数据过滤条件，格式同METADATA_RETRIEVAL_PROPOSAL.md
        """

        # 使用增强的检索器，支持过滤参数
        if hasattr(self.retriever, 'search'):
            # 使用增强检索器的search方法，支持过滤
            docs = self.retriever.search(
                query=question,
                top_k=top_k or self.settings.top_k,
                filters=filters
            )

            # 转换为Document对象用于LLM处理
            doc_objects = []
            for doc_info in docs:
                doc_obj = Document(
                    page_content=doc_info['content'],
                    metadata={
                        'doc_id': doc_info['doc_id'],
                        'filename': doc_info['filename'],
                        'score': doc_info['score'],
                        'document_metadata': doc_info['metadata']
                    }
                )
                doc_objects.append(doc_obj)

            # 使用格式化函数和LLM生成答案
            context = self._format_docs(doc_objects)
            answer = self.llm.invoke(
                self.prompt.format(context=context, question=question),
                config={"run_name": "query-generation"}
            )

            return {
                "question": question,
                "answer": answer,
                "sources": [doc.metadata.get("doc_id", "") for doc in doc_objects],
                "retrieved_chunks": [
                    {
                        "doc_id": doc.metadata.get("doc_id", ""),
                        "content": doc.page_content,
                        "filename": doc.metadata.get("filename", ""),
                        "score": doc.metadata.get("score", doc.metadata.get("rerank_score", doc.metadata.get("distance", 1.0))),
                        "metadata": doc.metadata.get("document_metadata", {})
                    }
                    for doc in doc_objects
                ]
            }
        else:
            # 降级到基本实现（如果检索器不支持search方法）
            # 这里可以实现一个兼容性方案
            docs = self.retriever.get_relevant_documents(question)

            # 执行RAG查询
            answer = self.rag_chain.invoke(question)

            return {
                "question": question,
                "answer": answer,
                "sources": [doc.metadata.get("doc_id", "") for doc in docs],
                "retrieved_chunks": [
                    {
                        "doc_id": doc.metadata.get("doc_id", ""),
                        "content": doc.page_content,
                        "filename": doc.metadata.get("filename", ""),
                        "score": doc.metadata.get("rerank_score", doc.metadata.get("distance", 1.0)),
                        "metadata": doc.metadata.get("document_metadata", {})
                    }
                    for doc in docs
                ]
            }
```

**验证**:
- 端到端功能测试
- 与原系统的输出对比
- API响应格式兼容性
- 元数据过滤参数兼容性

### 第八阶段：文档处理流程重构 (Step 7) - **增强以支持未来元数据**

**目标**: 使用LangChain文档加载器重构文档处理流程，**支持元数据提取**

**实现**:
```python
from langchain.document_loaders import PyMuPDFLoader, TextLoader
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import time
from datetime import datetime
import hashlib

class LangChainDocumentProcessor:
    def __init__(self, vectorstore):
        self.vectorstore = vectorstore

    def compute_file_hash(self, file_path: str, chunk_size: int = 8192, max_file_size: int = 100 * 1024 * 1024) -> str:
        """
        Compute MD5 hash for file with streaming support for large files.

        Args:
            file_path: Path to file
            chunk_size: Read chunk size in bytes (default: 8KB)
            max_file_size: Maximum file size to process (default: 100MB)

        Returns:
            MD5 hex digest string

        Raises:
            IOError: If file cannot be read
            MemoryError: If file exceeds max_file_size
        """
        try:
            file_size = os.path.getsize(file_path)

            # Check file size limit
            if file_size > max_file_size:
                raise MemoryError(f"File size {file_size} exceeds limit {max_file_size}")

            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Stream file in chunks to handle large files
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    hash_md5.update(chunk)

            return hash_md5.hexdigest()

        except (IOError, OSError) as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise IOError(f"Cannot compute hash for {file_path}: {e}")
        except MemoryError as e:
            logger.error(f"File too large: {file_path} ({file_size} bytes)")
            raise

    def process_document(self, file_path: str, metadata: dict = None):
        """
        处理单个文档（支持元数据）

        Args:
            file_path: 文件路径
            metadata: 额外的元数据，对应METADATA_RETRIEVAL_PROPOSAL.md中的字段
        """
        # 提取基础文件元数据
        stat_info = os.stat(file_path)
        file_metadata = {
            "filename": os.path.basename(file_path),
            "source": file_path,
            "file_size": stat_info.st_size,
            "modified_date": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "created_date": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "file_hash": self.compute_file_hash(file_path),
            "file_extension": os.path.splitext(file_path)[1].lower()
        }

        # 合并用户提供的元数据
        if metadata:
            file_metadata.update(metadata)

        # 根据文件类型选择加载器
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".pdf":
            loader = PyMuPDFLoader(file_path)
        elif file_ext == ".txt":
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            # 使用通用加载器
            loader = UnstructuredFileLoader(file_path)

        # 加载文档
        documents = loader.load()

        # 分块处理
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        chunks = text_splitter.split_documents(documents)

        # 添加元数据
        doc_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)

        for chunk in chunks:
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["filename"] = filename
            chunk.metadata["source"] = file_path
            chunk.metadata["file_metadata"] = file_metadata

            # 添加提案中提到的元数据字段（预留）
            chunk.metadata["document_type"] = file_metadata.get("file_extension", "unknown")
            chunk.metadata["created_date"] = file_metadata.get("created_date", datetime.now().isoformat())
            chunk.metadata["author"] = file_metadata.get("author", "system")
            chunk.metadata["department"] = file_metadata.get("department", "general")
            chunk.metadata["security_level"] = file_metadata.get("security_level", "public")
            chunk.metadata["tags"] = file_metadata.get("tags", [])

        # 存储到向量数据库
        # 使用batch模式以提高性能
        chunk_ids = self.vectorstore.add_documents(chunks)

        return {
            "doc_id": doc_id,
            "filename": filename,
            "chunks_count": len(chunks),
            "chunk_ids": chunk_ids,
            "metadata": file_metadata
        }

    def process_documents_batch(self, file_paths: list[str], metadata_list: list[dict] = None):
        """
        批量处理文档

        Args:
            file_paths: 文件路径列表
            metadata_list: 对应的元数据列表（可选）
        """
        results = []
        for i, file_path in enumerate(file_paths):
            meta = metadata_list[i] if metadata_list and i < len(metadata_list) else None
            result = self.process_document(file_path, meta)
            results.append(result)

        return results
```

## 性能基准测试方法论

### 基准测试指标定义
1. **查询延迟**:
   - P50, P95, P99 查询响应时间
   - 各组件（检索、重排、LLM生成）耗时分解
2. **准确性**:
   - 召回率 (Recall@K)
   - 精确率 (Precision@K)
   - 答案相关性评分
3. **吞吐量**:
   - 每秒查询数 (QPS)
   - 并发用户数下的性能表现
4. **资源使用**:
   - CPU/内存使用率
   - 数据库连接数

### 基准测试流程
1. **迁移前基准 (Baseline)**:
   - 运行当前系统性能测试
   - 记录所有关键指标
   - 保存测试数据集和问题集

2. **迁移中基准备**:
   - 每完成一个组件迁移后运行基准测试
   - 对比当前性能与基线
   - 性能下降超过5%则暂停并优化

3. **迁移后验证**:
   - 完整端到端性能测试
   - 与迁移前基线进行对比
   - 生成性能变化报告

### 基准测试脚本示例
```python
import time
import statistics
from typing import List, Dict, Any
from contextlib import contextmanager

@contextmanager
def get_accuracy_model():
    """
    Context manager for SentenceTransformer model lifecycle management.
    Ensures proper resource cleanup and prevents memory leaks.
    """
    from sentence_transformers import SentenceTransformer
    model = None
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        yield model
    finally:
        if model is not None:
            # Clear model from memory
            del model
            import gc
            gc.collect()

def calculate_accuracy(response: str, expected: str, threshold: float = 0.8) -> float:
    """
    Calculate semantic similarity between response and expected answer.
    Uses context manager to prevent memory leaks.

    Args:
        response: Generated answer from RAG system
        expected: Expected/ground truth answer
        threshold: Similarity threshold for binary classification

    Returns:
        Similarity score (0.0-1.0)
    """
    try:
        with get_accuracy_model() as model:
            embeddings = model.encode([response, expected])
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
    except Exception as e:
        import logging
        logging.error(f"Accuracy calculation failed: {e}")
        return 0.0

def run_benchmark_test(rag_system, test_dataset: List[Dict[str, str]], iterations: int = 10):
    """
    运行基准性能测试
    """
    results = {
        'query_times': [],
        'accuracies': [],
        'throughput': 0,
        'memory_usage': []
    }

    start_time = time.time()

    for i in range(iterations):
        for test_case in test_dataset:
            question = test_case['question']
            expected_answer = test_case.get('expected_answer')

            # 记录查询开始时间
            query_start = time.time()

            # 执行查询（包含元数据过滤测试）
            if 'filters' in test_case:
                # 测试带过滤的查询
                response = rag_system.query(question, filters=test_case['filters'])
            else:
                # 测试普通查询
                response = rag_system.query(question)

            # 记录查询结束时间
            query_end = time.time()
            query_time = query_end - query_start

            results['query_times'].append(query_time)

            # 简单准确性评估 (可以根据需要扩展)
            if expected_answer:
                accuracy = calculate_accuracy(response['answer'], expected_answer)
                results['accuracies'].append(accuracy)

    total_time = time.time() - start_time
    results['throughput'] = (iterations * len(test_dataset)) / total_time

    # 计算统计指标
    results['p50_time'] = statistics.median(results['query_times'])
    results['p95_time'] = statistics.quantiles(results['query_times'], n=20)[19]  # 95th percentile
    results['avg_time'] = statistics.mean(results['query_times'])
    results['accuracy_avg'] = statistics.mean(results['accuracies']) if results['accuracies'] else 0

    return results
```

## LangSmith 集成详解

### 环境配置
在每个迁移阶段启用LangSmith追踪：

```python
# 全局配置
import os
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = f"migration-step-{current_step}"

# 在代码中使用
from langchain_core.runnables import RunnableConfig

# 为特定运行添加配置
config = RunnableConfig(
    run_name=f"step-{current_step}-test",
    tags=[f"migration-step-{current_step}", "performance-test", "metadata-filtering-test"]
)
```

### 追踪和调试优势
1. **链路追踪**: 清晰展示每个组件的输入、输出和耗时
2. **性能分析**: 识别性能瓶颈和优化点
3. **调试支持**: 快速定位问题组件
4. **版本对比**: 对比不同实现的效果差异
5. **元数据过滤追踪**: 追踪过滤条件对检索结果的影响

## 未来元数据过滤功能的实施路径

基于 METADATA_RETRIEVAL_PROPOSAL.md 的增强架构，当元数据过滤功能需要实施时：

### 步骤1: 数据库架构扩展
```sql
-- 添加元数据字段（如METADATA_RETRIEVAL_PROPOSAL.md所述）
ALTER TABLE documents ADD COLUMN IF NOT EXISTS
    document_type TEXT,
    created_date DATE,
    modified_date DATE,
    author TEXT,
    department TEXT,
    tags TEXT[],
    security_level TEXT,
    metadata JSONB;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(created_date);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);
```

### 步骤2: 功能激活
由于架构已经预留了接口，只需：
1. 在文档加载时设置元数据字段
2. 在查询时使用filters参数
3. 验证过滤功能正常工作

## 风险评估与缓解

### 主要风险
1. **性能下降**: 抽象层可能带来额外开销
2. **兼容性问题**: 与现有数据格式的兼容性
3. **功能缺失**: 某些自定义功能难以通过LangChain实现
4. **复杂度增加**: 为未来功能预留的架构可能暂时显得复杂

### 缓解策略
1. **渐进式迁移**: 每步验证，降低风险
2. **并行验证**: 新旧系统并行测试，确保一致性
3. **性能监控**: 每步都进行基准测试
4. **回滚计划**: 每个阶段完成后保留回滚能力
5. **架构简化**: 对于暂时不需要的功能保留简单实现

## 实施时间估算

- **第1-3阶段 (环境准备、LLM、Embedder)**: 3-4天
- **第4阶段 (VectorStore增强)**: 3-4天 (略长因为预留元数据功能)
- **第5阶段 (HybridRetriever增强)**: 4-5天 (最长，需要完整实现)
- **第6-8阶段 (Reranker、RAG、DocumentProcessor)**: 4-5天
- **全面测试和优化**: 4-5天
- **总计**: 18-23天 (比原计划略长，但架构更健壮)

## 成功标准

1. **功能等价**: 所有现有功能在新系统中正常工作
2. **性能达标**: 关键性能指标不低于迁移前95%
3. **可维护性**: 代码复杂度降低，易于扩展
4. **可观测性**: LangSmith追踪正常工作，便于调试
5. **扩展性**: 为未来元数据过滤功能预留了接口

## 后续步骤

1. 从第一阶段开始实施，逐步推进到第二阶段
2. 每完成一个阶段，进行全面验证
3. 根据基准测试结果调整后续计划
4. 最终完成完整的LangChain 1.0迁移，同时保持未来扩展能力
