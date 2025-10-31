.PHONY: help setup start stop test clean

help:
	@echo "可用命令:"
	@echo "  make setup   - 初始化环境（首次运行）"
	@echo "  make start   - 启动API服务"
	@echo "  make stop    - 停止API服务"
	@echo "  make test    - 运行RAG测试"
	@echo "  make clean   - 清理数据库数据"

setup:
	@echo "🚀 初始化环境..."
	@bash scripts/setup_local.sh

start:
	@echo "▶️  启动API服务..."
	@echo "确保PostgreSQL和Redis已启动: brew services list"
	cd backend && python main.py

stop:
	@echo "⏸️  停止API服务（使用Ctrl+C）"
	@echo "如需停止数据库服务: brew services stop postgresql redis"

test:
	@echo "🧪 运行测试..."
	python scripts/test_rag.py

clean:
	@echo "🗑️  清理数据库数据..."
	psql ai_workflow -c "TRUNCATE TABLE document_chunks, documents CASCADE;"
	@echo "如需完全删除数据库: dropdb ai_workflow"
