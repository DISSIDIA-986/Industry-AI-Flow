# Database Optimization - Technical Design Document

## 概述
本文档描述了RAG系统和Prompt管理系统的数据库优化设计，包括索引策略、分区方案和性能优化。

## 架构设计
### 统一数据库架构
- 整合RAG和Prompt管理系统的数据模型
- 使用PostgreSQL + pgvector扩展
- 实现分区表和预聚合统计

### 索引优化策略
- 复合索引：prompts(category, is_active, priority DESC, performance_score DESC)
- 向量索引：document_chunks使用ivfflat索引
- 分区索引：prompt_usage_logs按月分区

## 性能优化
### 预聚合表
- prompt_daily_stats：每日使用统计
- prompt_weekly_stats：每周趋势分析
- prompt_monthly_stats：月度性能报告

### 查询优化
- 使用物化视图加速复杂查询
- 实现智能缓存策略
- 优化批量操作性能

## 实现计划
```sql
-- 1. 部署新的数据库架构
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 迁移现有数据
INSERT INTO prompts (name, category, content)
SELECT old_name, old_category, old_content FROM legacy_prompts;

-- 3. 实施性能监控
CREATE OR REPLACE FUNCTION performance_monitor()
RETURNS void AS $$
BEGIN
    -- 记录慢查询
    -- 更新性能统计
END;
$$ LANGUAGE plpgsql;
```

## 测试验证

### 功能测试
```python
def test_prompt_crud():
    """验证所有CRUD操作"""
    prompt = PromptManager.create("Test Prompt", "TEST", "content")
    assert prompt.id is not None

    updated = PromptManager.update(prompt.id, name="Updated Prompt")
    assert updated.name == "Updated Prompt"

    deleted = PromptManager.delete(prompt.id)
    assert deleted is True
```

### 性能测试
```sql
-- 对比优化前后的查询性能
EXPLAIN ANALYZE
SELECT p.name, p.performance_score
FROM prompts p
WHERE p.category = 'RAG'
  AND p.is_active = true
ORDER BY p.priority DESC, p.performance_score DESC
LIMIT 10;
```

### 压力测试
```bash
# 验证高并发场景下的稳定性
pgbench -i test_db
pgbench -c 50 -j 2 -t 1000 test_db
```

## 维护指南
```sql
-- 定期更新统计信息
ANALYZE prompts;
ANALYZE prompt_usage_logs;

-- 监控分区表大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename LIKE 'prompt_usage_logs_%';

-- 自动归档历史数据
CREATE OR REPLACE FUNCTION archive_old_data()
RETURNS void AS $$
BEGIN
    -- 归档6个月前的反馈数据
    INSERT INTO query_feedback_archive
    SELECT * FROM query_feedback
    WHERE created_at < CURRENT_DATE - INTERVAL '6 months';

    -- 归档1年前的操作日志
    INSERT INTO document_operations_log_archive
    SELECT * FROM document_operations_log
    WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;
```
