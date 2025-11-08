# 企业RAG系统文档归档最佳实践方案

> **版本**: v1.0
> **日期**: 2025-10-31
> **状态**: 推荐实施
> **适用**: Industry-AI-Flow RAG系统 (Phase 2完成后)

---

## 1. 方案概述

### 1.1 核心架构

**元数据与对象分离架构** - 业界标准最佳实践

```
┌─────────────────────────────────────────────────────────┐
│ 文档上传 → 元数据提取 → LLM智能分析 → 分类命名         │
│            ↓                                             │
│ PostgreSQL (元数据+小文件) + MinIO (大文件对象存储)     │
│            ↓                                             │
│ 自动分类 → 智能命名 → 分层存储 → 向量化索引             │
└─────────────────────────────────────────────────────────┘
```

**技术栈**：
- **元数据存储**: PostgreSQL 15+ (现有)
- **对象存储**: MinIO (Docker部署)
- **分类引擎**: Ollama qwen2.5:7b (现有)
- **向量检索**: pgvector (现有)
- **任务队列**: Python asyncio (轻量级，无需额外组件)

### 1.2 设计原则

1. **渐进式实施** - 3个Phase，从简单到复杂
2. **技术栈复用** - 使用现有PostgreSQL、Ollama、pgvector
3. **实用优先** - 避免过度设计，不引入Kafka、Celery等重型组件
4. **成本可控** - 仅需MinIO容器，无额外硬件成本
5. **向后兼容** - 不影响Phase 2已完成的RAG功能

---

## 2. 技术方案对比分析

### 2.1 四AI方案优劣对比

| 维度 | ChatGPT | Gemini | GLM | Qwen3 | **综合方案** |
|-----|---------|--------|-----|-------|------------|
| **架构复杂度** | 高 (事件驱动+消息队列) | 中 (异步+任务队列) | 中高 (企业全栈) | 高 (多层AI) | **中 (简化异步)** |
| **LLM策略** | 规则+LLM混合 | 异步LLM分析 | 多维度权重 | 监督学习 | **规则+LLM混合** |
| **命名方案** | doc_id驱动幂等 | 业务语义 | 业务语义 | 结构化 | **幂等+语义结合** |
| **存储分层** | 基础 | 基础 | 中等 | 详细 | **热温冷三层** |
| **实施周期** | 4-6周 | 3-4周 | 10周 | 6-8周 | **6周 (3 Phase)** |
| **技术债务** | 中 (消息队列) | 低 (任务队列) | 高 (完整系统) | 中 (AI训练) | **最低 (复用现有)** |

### 2.2 方案选择依据

**采纳**：
- ✅ Gemini: 异步处理架构（简化为Python asyncio）
- ✅ ChatGPT: 规则+LLM混合策略、幂等命名设计
- ✅ Qwen3: 存储分层策略（热温冷）、AI分类引擎设计
- ✅ GLM: 多维度分类体系（简化为3维）

**拒绝**：
- ❌ 事件驱动架构（Kafka/SQS）- 过度设计
- ❌ 任务队列（Celery/RQ）- 引入额外组件
- ❌ 复杂多租户隔离（独立bucket+KMS）- 当前无需求
- ❌ 监督学习分类器训练 - 缺少训练数据

---

## 3. 核心功能设计

### 3.1 智能分类体系（简化版）

**三维分类模型** - 平衡准确性与复杂度

| 分类维度 | 分类方法 | 分类项 | 存储路径 |
|---------|---------|-------|---------|
| **文档类型** | 规则+LLM | PDF/TXT/DOCX/XLSX/图片 | `docs/` |
| **业务领域** | LLM分析 | 技术/财务/法务/人事/市场/通用 | `{domain}/` |
| **时间维度** | 日期提取 | YYYY/MM/DD | `{year}/{month}/{day}/` |

**分类Prompt模板**：

```python
CLASSIFICATION_PROMPT = """你是文档管理专家。分析以下文档并返回JSON格式分类结果。

文档信息:
- 文件名: {filename}
- MIME类型: {mime_type}
- 内容节选 (前1000字): {content_preview}

返回JSON格式:
{{
  "domain": "技术|财务|法务|人事|市场|通用",
  "doc_type": "报告|合同|发票|手册|邮件|其他",
  "key_date": "YYYY-MM-DD|null",
  "title_keywords": ["关键词1", "关键词2", "关键词3"],
  "confidence": 0.0-1.0,
  "reason": "分类理由(50字内)"
}}

要求:
1. 置信度 <0.75 时，domain设为'通用'，doc_type设为'其他'
2. title_keywords提取2-3个最核心的业务关键词
3. key_date优先提取文档内的关键日期（合同日期、报告日期等）
"""
```

### 3.2 智能命名策略

**命名格式** - 幂等性 + 可读性

```
{title_keywords}_{key_date}_{doc_id}.{ext}
```

**组成说明**：
- `title_keywords`: 2-3个核心关键词，下划线连接（LLM提取）
- `key_date`: YYYYMMDD格式（LLM提取或上传日期）
- `doc_id`: 文件内容SHA256前16位（保证幂等性）
- `ext`: 原始文件扩展名

**示例**：
```
原文件名: contract.pdf
生成命名: sales_agreement_techcorp_20251031_9f3c8a1b2e4d5f6a.pdf

原文件名: report.docx
生成命名: q3_financial_report_20251031_a1b2c3d4e5f6a7b8.docx

原文件名: image001.jpg
生成命名: product_screenshot_ui_20251031_1a2b3c4d5e6f7a8b.jpg
```

### 3.3 存储路径策略

**标准路径结构**：

```
{bucket}/tenants/{tenant_id}/{domain}/{year}/{month}/{day}/{filename}
```

**具体示例**：

```
rag-documents/
├── tenants/
│   └── default/
│       ├── tech/
│       │   └── 2025/
│       │       └── 10/
│       │           └── 31/
│       │               ├── rag_system_design_20251031_abc123.pdf
│       │               └── api_documentation_v2_20251031_def456.md
│       ├── finance/
│       │   └── 2025/10/31/
│       │       └── q3_expense_report_20251031_789xyz.xlsx
│       └── general/
│           └── 2025/10/31/
│               └── meeting_notes_team_20251031_fedcba.txt
```

**路径设计理由**：
1. **租户隔离**: `tenants/{tenant_id}` 支持未来多租户扩展
2. **业务分类**: `{domain}` 便于按业务领域检索
3. **时间分区**: `{year}/{month}/{day}` 便于生命周期管理
4. **扁平化**: 避免过深嵌套（GLM方案的5层目录过于复杂）

### 3.4 存储分层策略

**三层存储架构** - 性能与成本平衡

```
┌─────────────────────────────────────────────────────────┐
│ 热数据层 (0-90天)                                        │
│  • PostgreSQL: 元数据 + <1MB小文件                      │
│  • MinIO标准存储: 大文件                                 │
│  • 响应时间: <100ms                                     │
├─────────────────────────────────────────────────────────┤
│ 温数据层 (91-730天)                                      │
│  • MinIO标准存储: 所有文件                               │
│  • 响应时间: <500ms                                     │
├─────────────────────────────────────────────────────────┤
│ 冷数据层 (731天+)                                        │
│  • MinIO生命周期策略: 自动迁移至归档层                   │
│  • 响应时间: <5秒 (首次访问)                             │
└─────────────────────────────────────────────────────────┘
```

**迁移策略**：
- **自动迁移**: MinIO生命周期规则自动处理
- **手动触发**: 提供API支持强制归档
- **访问恢复**: 冷数据首次访问自动解冻

---

## 4. 数据库设计

### 4.1 文档元数据表

```sql
-- 文档元数据表 (扩展现有 documents 表)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS
    -- 存储路径
    object_key TEXT,                    -- MinIO对象键 (完整路径)
    storage_tier TEXT DEFAULT 'hot',    -- 存储层级: hot/warm/cold

    -- 文档分类
    domain TEXT,                        -- 业务领域
    doc_type TEXT,                      -- 文档类型
    key_date DATE,                      -- 关键日期

    -- 智能命名
    original_filename TEXT,             -- 原始文件名
    smart_filename TEXT,                -- 智能生成文件名
    title_keywords TEXT[],              -- 标题关键词

    -- 分类元数据
    classification_result JSONB,        -- LLM分类完整结果
    classification_confidence FLOAT,    -- 分类置信度

    -- 内容摘要
    content_hash TEXT,                  -- SHA256哈希 (幂等性)
    file_size BIGINT,                   -- 文件大小
    mime_type TEXT,                     -- MIME类型

    -- 生命周期
    last_accessed_at TIMESTAMP,         -- 最后访问时间
    archived_at TIMESTAMP;              -- 归档时间

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_documents_object_key ON documents(object_key);
CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain);
CREATE INDEX IF NOT EXISTS idx_documents_storage_tier ON documents(storage_tier);
CREATE INDEX IF NOT EXISTS idx_documents_key_date ON documents(key_date);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
```

### 4.2 分类审计表

```sql
-- 分类审计表 (可选，用于优化分类准确率)
CREATE TABLE IF NOT EXISTS document_classification_audit (
    id SERIAL PRIMARY KEY,
    doc_id UUID REFERENCES documents(id),
    predicted_domain TEXT,              -- LLM预测结果
    predicted_doc_type TEXT,
    actual_domain TEXT,                 -- 用户修正结果
    actual_doc_type TEXT,
    confidence FLOAT,
    feedback_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_classification_audit_doc_id ON document_classification_audit(doc_id);
```

---

## 5. 核心API设计

### 5.1 文档上传与分类API

```python
# backend/api/documents.py

@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile,
    tenant_id: str = "default"
) -> dict:
    """
    文档上传与智能分类

    流程:
    1. 接收文件上传
    2. 计算文件哈希（幂等性检查）
    3. 提取文件内容预览
    4. LLM智能分类
    5. 生成智能文件名和存储路径
    6. 上传至MinIO
    7. 记录元数据至PostgreSQL
    8. 触发向量化处理
    """
    # 1. 读取文件内容
    file_content = await file.read()
    content_hash = hashlib.sha256(file_content).hexdigest()[:16]

    # 2. 幂等性检查
    existing_doc = db.query(
        "SELECT id, object_key FROM documents WHERE content_hash = %s",
        (content_hash,)
    ).fetchone()

    if existing_doc:
        return {
            "status": "exists",
            "doc_id": existing_doc.id,
            "message": "文档已存在，跳过上传"
        }

    # 3. 提取内容预览（用于LLM分类）
    content_preview = extract_text_preview(file_content, max_length=1000)

    # 4. 规则引擎初步分类
    rule_classification = apply_rules(file.filename, file.content_type)

    # 5. LLM智能分类（仅当规则引擎置信度低时）
    if rule_classification.get("confidence", 0) < 0.75:
        llm_classification = await classify_with_llm(
            filename=file.filename,
            mime_type=file.content_type,
            content_preview=content_preview
        )
    else:
        llm_classification = rule_classification

    # 6. 生成智能文件名
    title_keywords = "_".join(llm_classification["title_keywords"][:3])
    key_date = llm_classification.get("key_date") or datetime.now().strftime("%Y%m%d")
    ext = os.path.splitext(file.filename)[1]
    smart_filename = f"{title_keywords}_{key_date}_{content_hash}{ext}"

    # 7. 生成存储路径
    domain = llm_classification["domain"]
    now = datetime.now()
    object_key = (
        f"tenants/{tenant_id}/{domain}/"
        f"{now.year}/{now.month:02d}/{now.day:02d}/"
        f"{smart_filename}"
    )

    # 8. 上传至MinIO
    minio_client.put_object(
        bucket_name="rag-documents",
        object_name=object_key,
        data=io.BytesIO(file_content),
        length=len(file_content),
        content_type=file.content_type
    )

    # 9. 记录元数据
    doc_id = db.insert("""
        INSERT INTO documents (
            filename, object_key, content_hash,
            domain, doc_type, key_date,
            original_filename, smart_filename, title_keywords,
            classification_result, classification_confidence,
            file_size, mime_type, storage_tier
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id
    """, (
        smart_filename, object_key, content_hash,
        domain, llm_classification["doc_type"], llm_classification.get("key_date"),
        file.filename, smart_filename, llm_classification["title_keywords"],
        json.dumps(llm_classification), llm_classification["confidence"],
        len(file_content), file.content_type, "hot"
    ))

    # 10. 异步触发向量化处理（复用Phase 2的Ingestion流程）
    asyncio.create_task(trigger_ingestion(doc_id))

    return {
        "status": "success",
        "doc_id": doc_id,
        "object_key": object_key,
        "smart_filename": smart_filename,
        "classification": llm_classification
    }
```

### 5.2 文档检索API

```python
@app.get("/api/v1/documents/search")
async def search_documents(
    query: str = None,
    domain: str = None,
    doc_type: str = None,
    date_from: str = None,
    date_to: str = None,
    tenant_id: str = "default",
    limit: int = 10
) -> dict:
    """
    多维度文档检索

    支持:
    1. 关键词检索（文件名、标题关键词）
    2. 领域过滤（domain）
    3. 类型过滤（doc_type）
    4. 日期范围过滤
    """
    where_clauses = ["1=1"]
    params = []

    if query:
        where_clauses.append(
            "(filename ILIKE %s OR %s = ANY(title_keywords))"
        )
        params.extend([f"%{query}%", query])

    if domain:
        where_clauses.append("domain = %s")
        params.append(domain)

    if doc_type:
        where_clauses.append("doc_type = %s")
        params.append(doc_type)

    if date_from:
        where_clauses.append("key_date >= %s")
        params.append(date_from)

    if date_to:
        where_clauses.append("key_date <= %s")
        params.append(date_to)

    params.append(limit)

    sql = f"""
        SELECT
            id, filename, smart_filename, object_key,
            domain, doc_type, key_date, title_keywords,
            classification_confidence, file_size, uploaded_at
        FROM documents
        WHERE {" AND ".join(where_clauses)}
        ORDER BY uploaded_at DESC
        LIMIT %s
    """

    results = db.query(sql, tuple(params)).fetchall()

    return {
        "total": len(results),
        "documents": [
            {
                "id": row.id,
                "filename": row.smart_filename,
                "domain": row.domain,
                "doc_type": row.doc_type,
                "key_date": row.key_date,
                "keywords": row.title_keywords,
                "confidence": row.classification_confidence,
                "size": row.file_size,
                "uploaded_at": row.uploaded_at,
                "download_url": f"/api/v1/documents/{row.id}/download"
            }
            for row in results
        ]
    }
```

---

## 6. 实施路线图

### Phase 1: 基础存储 (1-2周)

**目标**: 建立对象存储基础设施

**任务清单**:
- [ ] 部署MinIO容器（Docker Compose）
- [ ] 扩展documents表结构（新增字段）
- [ ] 实现基础文件上传API
- [ ] 实现MinIO文件存储逻辑
- [ ] 实现文件下载API
- [ ] 编写单元测试

**验收标准**:
- ✅ MinIO正常运行，Console可访问
- ✅ 文件上传成功率 100%
- ✅ 文件下载成功率 100%
- ✅ 元数据正确记录到PostgreSQL

**技术细节**:

```yaml
# infra/docker-compose.yaml (新增MinIO服务)
minio:
  image: minio/minio:latest
  container_name: rag_minio
  ports:
    - "9000:9000"  # API端口
    - "9001:9001"  # Console端口
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin123
  command: server /data --console-address ":9001"
  volumes:
    - minio_data:/data
  networks:
    - rag_network

volumes:
  minio_data:
```

### Phase 2: 智能分类 (2-3周)

**目标**: 实现LLM驱动的文档智能分类和命名

**任务清单**:
- [ ] 实现规则引擎（基于文件扩展名、MIME类型）
- [ ] 实现LLM分类Prompt模板
- [ ] 集成Ollama qwen2.5分类引擎
- [ ] 实现智能文件命名生成
- [ ] 实现存储路径生成逻辑
- [ ] 实现幂等性检查（基于content_hash）
- [ ] 实现分类结果审计功能
- [ ] 编写集成测试

**验收标准**:
- ✅ 规则引擎准确率 >90%（常见文件类型）
- ✅ LLM分类准确率 >80%（人工抽样验证）
- ✅ 文件命名可读性满意度 >80%
- ✅ 幂等性检查准确率 100%

**核心代码**:

```python
# backend/services/document_classifier.py

async def classify_with_llm(
    filename: str,
    mime_type: str,
    content_preview: str
) -> dict:
    """使用LLM进行文档分类"""
    prompt = CLASSIFICATION_PROMPT.format(
        filename=filename,
        mime_type=mime_type,
        content_preview=content_preview
    )

    response = await ollama_client.generate(prompt)

    try:
        result = json.loads(response)
        # 验证必需字段
        assert "domain" in result
        assert "doc_type" in result
        assert "confidence" in result
        return result
    except (json.JSONDecodeError, AssertionError):
        # LLM返回格式错误，降级为通用分类
        return {
            "domain": "general",
            "doc_type": "other",
            "key_date": None,
            "title_keywords": [filename.split(".")[0]],
            "confidence": 0.5,
            "reason": "LLM分类失败，降级为通用分类"
        }
```

### Phase 3: 生命周期管理 (2-3周)

**目标**: 实现存储分层和自动归档

**任务清单**:
- [ ] 配置MinIO生命周期策略
- [ ] 实现存储层级迁移脚本（hot→warm→cold）
- [ ] 实现访问频率统计
- [ ] 实现自动归档定时任务
- [ ] 实现冷数据恢复API
- [ ] 实现存储成本监控
- [ ] 编写性能测试

**验收标准**:
- ✅ 90天后自动迁移至温数据层
- ✅ 2年后自动迁移至冷数据层
- ✅ 冷数据恢复时间 <5秒
- ✅ 存储成本降低 >30%

**MinIO生命周期配置**:

```json
{
  "Rules": [
    {
      "ID": "Move to warm tier",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "tenants/"
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "ID": "Archive old documents",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "tenants/"
      },
      "Transitions": [
        {
          "Days": 730,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

---

## 7. 性能与成本

### 7.1 性能指标

| 指标 | 目标值 | 监控方法 |
|-----|--------|---------|
| **上传延迟** | <2秒 (10MB文件) | Prometheus + Grafana |
| **下载延迟** | <500ms (10MB文件) | Prometheus + Grafana |
| **分类延迟** | <5秒 (LLM分析) | 应用日志 |
| **检索延迟** | <200ms (元数据查询) | PostgreSQL慢查询日志 |
| **存储可用性** | >99.5% | MinIO健康检查 |
| **分类准确率** | >80% | 人工抽样审计 |

### 7.2 成本估算

**硬件成本** (基于1TB文档、1000文档/月上传量):

| 资源 | 配置 | 月成本 | 年成本 |
|-----|------|--------|--------|
| **MinIO存储** | 1TB SSD | ¥200 | ¥2,400 |
| **PostgreSQL扩容** | +20GB | ¥50 | ¥600 |
| **备份存储** | 500GB | ¥100 | ¥1,200 |
| **总计** | | **¥350/月** | **¥4,200/年** |

**运维成本**:
- 初始部署: 2-3天
- 日常维护: 2小时/月
- 监控告警: 自动化（无额外成本）

### 7.3 成本优化措施

1. **存储分层** - 热数据30%、温数据50%、冷数据20% → 成本降低40%
2. **内容去重** - 基于SHA256哈希，相同文件仅存一份 → 节省10-20%
3. **智能压缩** - MinIO自动压缩，平均压缩率30% → 成本降低30%
4. **生命周期自动化** - 无需人工干预，运维成本降低80%

**预期ROI**:
- **成本**: ¥4,200/年 + 维护时间24小时/年
- **收益**: 文档检索效率提升50%、人工整理时间节省70%、存储成本降低40%
- **投资回收期**: <6个月

---

## 8. 风险与缓解

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| **LLM分类不准确** | 中 | 中 | 规则引擎前置、人工审计反馈、持续优化Prompt |
| **MinIO性能瓶颈** | 高 | 低 | 负载测试、分布式部署、CDN加速 |
| **存储成本超预算** | 中 | 低 | 生命周期管理、定期成本审计、容量告警 |
| **数据丢失** | 高 | 极低 | MinIO纠删码、定期备份、异地容灾 |
| **向量化失败** | 中 | 低 | 异步重试、错误队列、人工介入 |

### 8.2 实施风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| **实施周期延误** | 低 | 中 | 渐进式发布、MVP优先、并行开发 |
| **与现有系统冲突** | 中 | 低 | 充分测试、灰度发布、回滚方案 |
| **用户接受度低** | 低 | 低 | 提供手动修正功能、收集反馈、迭代优化 |

---

## 9. 监控与运维

### 9.1 关键监控指标

```python
# backend/services/monitoring.py

METRICS = {
    "upload_count": "文档上传总数",
    "upload_success_rate": "上传成功率",
    "classification_accuracy": "分类准确率",
    "storage_usage": "存储空间使用量",
    "hot_tier_size": "热数据层大小",
    "warm_tier_size": "温数据层大小",
    "cold_tier_size": "冷数据层大小",
    "avg_upload_latency": "平均上传延迟",
    "avg_classification_latency": "平均分类延迟",
    "minio_availability": "MinIO可用性"
}
```

### 9.2 告警规则

```yaml
alerts:
  - name: high_upload_failure_rate
    condition: upload_success_rate < 95%
    severity: warning
    action: 通知运维团队

  - name: storage_capacity_high
    condition: storage_usage > 80%
    severity: warning
    action: 扩容提醒

  - name: minio_unavailable
    condition: minio_availability < 99%
    severity: critical
    action: 立即通知、自动重启

  - name: classification_accuracy_low
    condition: classification_accuracy < 75%
    severity: warning
    action: 优化Prompt、检查LLM服务
```

---

## 10. 总结与建议

### 10.1 方案优势

1. **架构简洁** - 无额外重型组件（Kafka、Celery），维护成本低
2. **技术复用** - 充分利用现有PostgreSQL、Ollama、pgvector
3. **渐进实施** - 3个Phase，可分阶段验证效果
4. **成本可控** - 年成本¥4,200，投资回收期 <6个月
5. **扩展性强** - 支持未来多租户、分布式部署、云上迁移

### 10.2 实施建议

**立即执行**:
- Phase 1（基础存储）- 为RAG系统建立文档持久化能力

**短期规划** (3个月内):
- Phase 2（智能分类）- 提升文档管理效率和检索准确性

**长期规划** (6个月内):
- Phase 3（生命周期管理）- 优化存储成本和系统性能

### 10.3 成功关键因素

1. **Prompt工程** - LLM分类准确率的核心，需持续优化
2. **用户反馈** - 建立分类审计机制，持续改进
3. **监控告警** - 及时发现问题，保障系统稳定
4. **文档规范** - 建立企业文档管理规范，提升分类效果

---

## 附录A: 快速开始

### A.1 部署MinIO

```bash
# 1. 更新 docker-compose.yaml
cd infra
# (添加MinIO服务配置)

# 2. 启动MinIO
docker-compose up -d minio

# 3. 访问MinIO Console
open http://localhost:9001
# 用户名: minioadmin
# 密码: minioadmin123

# 4. 创建bucket
mc alias set local http://localhost:9000 minioadmin minioadmin123
mc mb local/rag-documents
mc policy set download local/rag-documents
```

### A.2 数据库迁移

```bash
# 执行SQL迁移脚本
psql -U postgres -d ai_workflow -f backend/migrations/001_add_document_archiving.sql
```

### A.3 配置环境变量

```bash
# .env (新增配置)
# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=rag-documents
MINIO_USE_SSL=false

# 存储策略
STORAGE_HOT_DAYS=90
STORAGE_WARM_DAYS=730
```

---

**文档版本**: v1.0
**最后更新**: 2025-10-31
**维护者**: AI开发团队
