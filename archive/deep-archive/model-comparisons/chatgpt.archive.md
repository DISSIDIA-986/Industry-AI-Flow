# OSS 自动分类与命名方案（补充）

本文回答“文档上传到对象存储（OSS, Object Storage Service）后，如何让大语言模型（LLM, Large Language Model）基于内容或元数据自动分类存储，并自动创建 bucket/folder、重命名文件”为目标，给出可行落地方案。

## 1. 目标与约束
- 目标：自动识别文档类型/租户/业务线，落库并在 OSS 中放置到正确路径，生成“可读且稳定”的文件名；保证幂等、可回滚、审计可追踪。
- 约束：S3/MinIO 无“移动”操作，需 Copy+Delete；对象锁（WORM）可能禁止删除；创建 bucket 需权限与配额限制；多租户隔离与 KMS（Key Management Service）分钥；GDPR/合规可删除与追溯。

## 2. 总体架构
- 触发：ObjectCreated 事件（S3 Event/MinIO Notification）→ 消息队列（Kafka/SQS/RabbitMQ）→ 分类与命名微服务 → Copy（到目标 key）→ 更新元数据表（PostgreSQL）→ 可选：删除源对象/保留版本。
- 依赖：
  - OSS：S3/MinIO/Azure Blob/GCS
  - 元数据与映射：PostgreSQL（object_id, original_key, new_key, doc_id, tenant_id, doc_type, confidence, status）
  - LLM 服务：本地 vLLM/Ollama（Qwen2.5/7B 级）或调用云 API（如企业内私有化）
  - 扩展：杀毒（ClamAV）、PII（Personally Identifiable Information）检测、OCR（Optical Character Recognition）

## 3. 可行方案
- 方案A：规则映射（无 LLM）
  - 基于 MIME、文件扩展名、上传 header、表单字段、正则（文件名/路径/内容关键字）、业务枚举映射 doc_type、tenant。
  - 优点：确定性强、低成本、可提前校验；缺点：覆盖有限，需持续维护规则。
- 方案B：LLM 分类（弱结构化/半结构化）
  - 文本抽取（PDF→文本，图片→OCR），Prompt 分类出 doc_type、部门、日期、客户名等；置信度+理由；不确定时回退队列。
  - 优点：泛化强、适配复杂文档；缺点：需要算力与延迟控制，需对抗幻觉与一致性。
- 方案C：混合（推荐）
  - 先规则快速判定（高精度场景，如发票/合同模板），不确定再走 LLM；可配置白名单/黑名单与人工复核流转。

## 4. Bucket/Folder 与命名策略
- Bucket 策略：
  - 中小规模："env-tenant"（如 prod-acme）；大规模/强隔离：每租户独立 bucket + 独立 KMS key；公共只读素材独立 bucket。
- 目录（prefix）建议：
  - tenant_id/doc_type/yyyy/mm/dd/source/model_v/ 例如：acme/invoice/2025/10/31/email/ocr-v2/
- 文件命名：可读 + 稳定 + 去重
  - 格式：{normalized_title}.{doc_id}.{version}.{ext}
  - doc_id = sha256(file_bytes) 或 ULID（与元数据映射）；version 用对象版本或内部修订号。
  - 示例：signed_contract.acme-abc-987.sha256_9f3c….v1.pdf
- 幂等：以 doc_id 驱动目标 key 生成；重复上传同一内容映射到同一路径。

## 5. 自动创建 bucket/folder
- 创建 bucket：在分类微服务内按策略检查并延迟创建（idempotent）；为新 bucket 自动配置：版本化、SSE-KMS、生命周期、标签（owner=tenant）。
- 创建 folder：以对象前缀方式天然存在，无需显式创建；首次写入即可。

## 6. 重命名与移动的实现
- S3/MinIO 无原子移动：执行 CopyObject(new_key) → 校验 ETag/sha256 → Put object tags/metadata → Update DB → 依据策略 DeleteObject(old_key)。
- WORM/对象锁开启时：保留源对象，仅新增目标副本，DB 记录“canonical_key=new_key”。
- 事务一致性：用业务层“事务外盒”实现（先写 DB pending → 完成复制 → 提交/补偿），失败进入补偿队列重试。

## 7. LLM 分类 Prompt 模板示例
```
你是企业文档分类器。请基于以下文本节选与元数据，返回 JSON（严格遵守 schema）。
元数据: {mime, filename, uploader, tenant_hint}
文本节选(最多1000字): "..."
Schema:
{
  "doc_type": "invoice|contract|policy|report|other",
  "title": "简洁标题(<=80字)",
  "date": "YYYY-MM-DD|null",
  "customer": "string|null",
  "department": "string|null",
  "confidence": 0-1,
  "reason": "简述理由(<=120字)"
}
若置信度<0.75，设置 doc_type=other 并降低风险性推断。
```

## 8. 最小可行实现（MVP，基于 MinIO）
1) MinIO Bucket Notification → NATS/Kafka
2) Ingest 服务：下载对象→杀毒→OCR/抽取→规则判定；若不确定调用本地 vLLM（Qwen2.5-7B）
3) 以 doc_id 生成目标 key 与命名；若 bucket 不存在则创建并应用策略
4) CopyObject 到目标 key；写入 PostgreSQL 映射表；打标签 tags: {tenant, doc_type, doc_id}
5) 置信度>=0.75 且无锁删除源对象；否则保留并人工复核

## 9. 伪代码（Python，boto3 逻辑类似 MinIO SDK）
```python
from hashlib import sha256
from minio import Minio

minio = Minio("minio.local:9000", access_key="...", secret_key="...", secure=False)

def doc_id_of(obj_bytes):
    return sha256(obj_bytes).hexdigest()[:32]

def target_key(tenant, doc_type, dt, title, doc_id, ext):
    y,m,d = dt.split("-")
    safe_title = title.lower().replace(" ", "-")[:64]
    return f"{tenant}/{doc_type}/{y}/{m}/{d}/ingest/ocr-v1/{safe_title}.{doc_id}.v1.{ext}"

# 事件处理
bucket, key = event.bucket, event.key
obj = minio.get_object(bucket, key).read()
info = classify_with_rules_and_llm(obj, key, event.metadata)
if not bucket_exists(info.tenant): create_bucket_and_policies(info.tenant)
dst_key = target_key(info.tenant, info.doc_type, info.date or today(), info.title, doc_id_of(obj), ext_of(key))
minio.copy_object(info.tenant, dst_key, f"/{bucket}/{key}")
write_db_mapping(original_key=key, new_key=dst_key, meta=info)
if deletable(bucket, key): minio.remove_object(bucket, key)
```

## 10. 风险与缓解
- 幻觉/误判：使用阈值与规则前置、抽样人工复核；保留原始对象与可回滚映射。
- 性能：批量/并行处理、缓存 OCR 结果、限制 LLM 上下文长度、采用小模型；对大对象用分段下载与分段 Copy。
- 安全：SSE-KMS、最小权限（IAM, Identity and Access Management）、审计日志、对象锁策略。
- 法务：保留版本与审计；删除遵循“可删除权”需映射反查，执行 Delete Mark + 合规清理。

## 11. 指标与验收
- 分类准确率/召回率、置信度分布；平均处理时延 P50/P95；重试率；人工复核通过率；命名冲突率=0；幂等冲突率<1e-6。

## 12. 推荐
- 采用“规则优先 + LLM 兜底”的混合方案；以 doc_id 驱动幂等命名；bucket 按租户或“env-tenant”划分；事件驱动、可审计、可回滚。
