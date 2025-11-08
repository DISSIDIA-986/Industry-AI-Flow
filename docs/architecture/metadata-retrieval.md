# 元数据检索功能提案

**日期**: 2025-10-31
**状态**: 提案（未实施）
**优先级**: 低（Phase 3或实际应用阶段）

---

## 📊 背景分析

### 当前检索能力对比

| 检索类型 | 实现状态 | 完整度 | 说明 |
|---------|---------|--------|------|
| 关键词检索 | ✅ 完整 | 100% | BM25 + jieba分词 |
| 语义检索 | ✅ 完整 | 100% | pgvector + 768维向量 |
| 混合检索 | ✅ 完整 | 100% | RRF融合算法 |
| 重排序 | ✅ 完整 | 100% | bge-reranker |
| **元数据检索** | ❌ 缺失 | 0% | 无过滤接口 |

**总体完整度**: 85%

---

## 🤔 是否需要实施？

### ❌ 不建议立即实施

#### 理由

**1. Phase 2目标已达成**
- 准确率: 20% → 80% ✅ (超越70%目标)
- P95延迟: 5.82秒 ✅ (<10秒目标)
- 所有验收指标达标 ✅

**2. 当前测试场景无此需求**

当前20个测试问题类型：
```
✅ "什么是RAG系统？"
✅ "pgvector的主要功能是什么？"
✅ "Python在这个项目中的作用？"
```

不需要元数据过滤：
```
❌ "去年Q3法务部关于数据隐私的合同"
❌ "2024年研发部发布的技术手册"
❌ "标记为'机密'的安全审计报告"
```

**3. 元数据检索是业务功能，非核心RAG技术**
- Phase 2专注：技术升级（嵌入、混合检索、重排序、OCR）
- 元数据检索：业务场景功能（按部门、时间、类型过滤）

**4. 实施成本 vs 收益**
- 简单实现：1-2天（基础过滤）
- 完整实现：1-2周（查询解析+元数据管理）
- **当前ROI低**：无实际应用场景验证

---

## ✅ 推荐时机

### Phase 3 或实际应用阶段

**触发条件**（满足任一即可考虑实施）：
1. 文档数量 >1000份，需要按类型/时间筛选
2. 多部门使用，需要按部门/权限过滤
3. 业务需求明确（如"查找去年的XX文档"）
4. 性能优化需求（先过滤再检索，减少向量计算）

---

## 📋 实施方案（如需要）

### 渐进式元数据检索（最小化实现）

#### Phase 1: 数据库扩展（30分钟）

**目标**: 添加基础元数据字段

```sql
-- infra/init.sql 或 migration script

-- 1. 扩展 documents 表
ALTER TABLE documents ADD COLUMN IF NOT EXISTS
    document_type TEXT,           -- 文档类型: 'pdf', 'txt', 'image', 'docx'
    created_date DATE,            -- 创建日期
    modified_date DATE,           -- 修改日期
    author TEXT,                  -- 作者
    department TEXT,              -- 部门
    tags TEXT[],                  -- 标签数组: ['技术文档', '内部资料']
    security_level TEXT,          -- 安全级别: 'public', 'internal', 'confidential'
    metadata JSONB;               -- 扩展元数据 (灵活字段)

-- 2. 添加索引（提升过滤性能）
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(created_date);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);

-- 3. 更新现有文档（补充元数据）
UPDATE documents SET
    document_type = CASE
        WHEN filename LIKE '%.pdf' THEN 'pdf'
        WHEN filename LIKE '%.txt' THEN 'txt'
        ELSE 'unknown'
    END,
    created_date = uploaded_at::date
WHERE document_type IS NULL;
```

---

#### Phase 2: 检索接口扩展（1-2小时）

**目标**: HybridRetriever 支持元数据过滤

**修改文件**: `backend/services/retrieval/hybrid_search.py`

```python
from typing import Optional, List, Dict

class HybridRetriever:
    # ... 现有代码 ...

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,  # 新增：元数据过滤
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict]:
        """
        混合检索（支持元数据过滤）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 元数据过滤条件
            vector_weight: 向量检索权重
            bm25_weight: BM25检索权重

        filters 示例:
        {
            "document_type": "pdf",
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-12-31"
            },
            "department": "研发部",
            "tags": ["技术文档", "内部资料"],  # 包含任一标签
            "security_level": "internal"
        }

        Returns:
            检索结果列表
        """
        # 1. 应用元数据过滤（获取符合条件的文档ID）
        filtered_doc_ids = None
        if filters:
            filtered_doc_ids = self._apply_metadata_filters(filters)

            # 如果过滤后无文档，直接返回空
            if not filtered_doc_ids:
                return []

        # 2. 在过滤后的文档中执行向量检索
        query_embedding = embed_single_text(query)
        vector_results = self.vector_store.similarity_search(
            query_embedding,
            top_k=top_k * 2,
            doc_ids=filtered_doc_ids  # 传入过滤后的文档ID
        )

        # 3. 在过滤后的文档中执行BM25检索
        if filtered_doc_ids:
            # 过滤 doc_chunks，只保留符合条件的文档
            filtered_chunks = [
                chunk for chunk in self.doc_chunks
                if chunk['doc_id'] in filtered_doc_ids
            ]
        else:
            filtered_chunks = self.doc_chunks

        # 重新构建BM25索引（针对过滤后的文档）
        # ... BM25检索逻辑 ...

        # 4. RRF 融合
        # ... 现有融合逻辑 ...

        return final_results

    def _apply_metadata_filters(self, filters: Dict) -> List[str]:
        """
        应用元数据过滤，返回符合条件的文档ID列表

        Args:
            filters: 过滤条件字典

        Returns:
            符合条件的文档UUID列表
        """
        conn = self.vector_store.get_connection()
        cur = conn.cursor()

        try:
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

            # 构建SQL
            if not where_clauses:
                return None  # 无过滤条件

            where_sql = " AND ".join(where_clauses)
            sql = f"SELECT id FROM documents WHERE {where_sql}"

            cur.execute(sql, tuple(params))
            doc_ids = [row[0] for row in cur.fetchall()]

            print(f"📌 元数据过滤: {len(doc_ids)} 个文档符合条件")
            return doc_ids

        finally:
            cur.close()
```

---

#### Phase 3: VectorStore 适配（1小时）

**目标**: 支持预过滤的文档ID列表

**修改文件**: `backend/services/vectorstore.py`

```python
def similarity_search(
    self,
    query_embedding: list[float],
    top_k: int = 3,
    doc_ids: Optional[List[str]] = None  # 新增：预过滤的文档ID
) -> list[dict]:
    """
    向量相似度搜索（支持文档ID过滤）

    Args:
        query_embedding: 查询向量
        top_k: 返回结果数量
        doc_ids: 预过滤的文档ID列表（None表示不过滤）

    Returns:
        检索结果列表
    """
    conn = self.get_connection()
    cur = conn.cursor()

    try:
        # 构建WHERE子句
        where_clause = ""
        params = []

        if doc_ids:
            # 仅在指定文档中检索
            placeholders = ','.join(['%s'] * len(doc_ids))
            where_clause = f"AND dc.doc_id IN ({placeholders})"
            params.extend(doc_ids)

        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        params.insert(0, embedding_str)
        params.append(top_k)

        sql = f"""
            SELECT
                dc.doc_id,
                dc.id as chunk_id,
                dc.content,
                dc.embedding <=> %s::vector AS distance,
                d.filename
            FROM document_chunks dc
            JOIN documents d ON dc.doc_id = d.id
            WHERE 1=1 {where_clause}
            ORDER BY distance
            LIMIT %s
        """

        cur.execute(sql, tuple(params))

        results = []
        for row in cur.fetchall():
            results.append({
                "doc_id": row[0],
                "chunk_id": row[1],
                "content": row[2],
                "distance": float(row[3]),
                "filename": row[4]
            })

        return results

    finally:
        cur.close()
        conn.close()
```

---

#### Phase 4: RAG Engine 集成（30分钟）

**目标**: 查询接口支持元数据过滤

**修改文件**: `backend/services/rag_engine.py`

```python
def query(
    self,
    question: str,
    top_k: int = None,
    filters: Optional[Dict] = None  # 新增
) -> dict:
    """
    RAG查询流程（支持元数据过滤）

    Args:
        question: 用户问题
        top_k: 返回结果数量
        filters: 元数据过滤条件

    Returns:
        查询结果
    """
    if top_k is None:
        top_k = settings.top_k

    # 使用混合检索（带元数据过滤）
    if self.use_hybrid_search and self.hybrid_retriever:
        similar_chunks = self.hybrid_retriever.search(
            query=question,
            top_k=retrieve_k,
            filters=filters,  # 传入过滤条件
            vector_weight=0.7,
            bm25_weight=0.3
        )
    else:
        # ... 纯向量检索逻辑 ...

    # ... 后续重排序和LLM生成逻辑 ...
```

---

### 使用示例

```python
from backend.services.rag_engine import SimpleRAG

rag = SimpleRAG()

# 1. 无过滤（当前用法）
result = rag.query("什么是RAG系统？")

# 2. 按文档类型过滤
result = rag.query(
    "什么是RAG系统？",
    filters={"document_type": "pdf"}
)

# 3. 按时间范围过滤
result = rag.query(
    "性能优化建议",
    filters={
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
)

# 4. 复合条件过滤
result = rag.query(
    "数据隐私合同",
    filters={
        "department": "法务部",
        "tags": ["合同", "隐私"],
        "date_range": {"start": "2024-01-01"}
    }
)
```

---

## 📊 预期效果

### 性能提升

**场景**: 10,000份文档，查询"去年的技术报告"

| 指标 | 无过滤 | 有过滤 | 提升 |
|------|--------|--------|------|
| 候选文档数 | 10,000 | ~500 | 95% ↓ |
| 向量计算量 | 10,000次 | 500次 | 95% ↓ |
| 查询延迟 | 5.8秒 | **0.8秒** | 86% ↓ |
| 准确率 | 80% | **90%+** | 12% ↑ |

### 功能扩展

- ✅ 支持复杂业务查询
- ✅ 多租户隔离（按部门过滤）
- ✅ 权限控制（按安全级别过滤）
- ✅ 时间范围筛选

---

## 🚧 实施风险

### 低风险
- ✅ 向后兼容（filters=None时使用现有逻辑）
- ✅ 数据库扩展简单（ALTER TABLE）
- ✅ 实施成本可控（1-2天）

### 需注意
- ⚠️ 需要补充现有文档的元数据
- ⚠️ 文档导入流程需增加元数据提取
- ⚠️ 过滤逻辑需要充分测试

---

## 🎯 决策建议

### 推荐：暂不实施，待实际应用阶段

**理由**：
1. ✅ Phase 2目标已达成
2. ✅ 当前无实际应用场景
3. ✅ 可按需快速实施（1-2天）
4. ⚠️ 避免过度优化

### 实施触发条件

满足**任一条件**时再考虑：
1. 文档数量 >1000份
2. 多部门/多用户使用
3. 明确的业务需求
4. 性能优化需求

---

**提案状态**: 未实施（待Phase 3或实际应用阶段）
**版本**: Metadata Retrieval Proposal v1.0
