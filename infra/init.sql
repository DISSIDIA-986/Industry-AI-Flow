-- 启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档表
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    chunk_count INTEGER DEFAULT 0
);

-- 创建文档块表（带向量列）
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 输出384维
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建向量索引（加速相似度搜索）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 为doc_id创建索引
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id);
