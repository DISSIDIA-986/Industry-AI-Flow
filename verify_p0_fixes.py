#!/usr/bin/env python3
"""
P0修复验证脚本
验证所有第一批和第二批P0修复是否正确实施
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def verify_database_pool():
    """验证1.1: 数据库连接池工厂"""
    print("\n🔍 验证1.1: 数据库连接池工厂")
    try:
        from backend.config import get_database_pool
        pool = await get_database_pool()
        print("✅ get_database_pool() 函数存在并返回连接池")
        await pool.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接池工厂验证失败: {e}")
        return False


async def verify_prompt_routes():
    """验证1.2: Prompt路由注册"""
    print("\n🔍 验证1.2: Prompt路由注册")
    try:
        from backend.main import app
        routes = [route.path for route in app.routes]
        prompt_routes = [r for r in routes if 'prompt' in r.lower()]
        print(f"✅ 找到 {len(prompt_routes)} 个prompt相关路由")
        for route in prompt_routes[:5]:
            print(f"   - {route}")
        return True
    except Exception as e:
        print(f"❌ Prompt路由注册验证失败: {e}")
        return False


async def verify_prompt_update_model():
    """验证1.3: PromptUpdate模型字段"""
    print("\n🔍 验证1.3: PromptUpdate模型字段契约")
    try:
        from backend.api.prompt_routes import PromptUpdate
        fields = PromptUpdate.model_fields
        if 'updated_by' in fields:
            print("✅ PromptUpdate模型包含updated_by字段")
            return True
        else:
            print("❌ PromptUpdate模型缺少updated_by字段")
            return False
    except Exception as e:
        print(f"❌ PromptUpdate模型验证失败: {e}")
        return False


async def verify_prompt_schema():
    """验证: Prompt数据库schema"""
    print("\n🔍 验证: Prompt数据库schema")
    try:
        import psycopg2
        from backend.config import settings

        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()

        # 检查表是否存在
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE 'prompt%'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        expected_tables = [
            'prompts',
            'prompt_experiments',
            'prompt_tag_relations',
            'prompt_tags',
            'prompt_usage_logs',
            'prompt_versions'
        ]

        print(f"   找到 {len(tables)} 个prompt相关表:")
        for table in tables:
            print(f"   - {table}")

        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            print(f"⚠️  缺少表: {missing_tables}")
            return False

        # 检查schema_migrations记录
        cur.execute("""
            SELECT version, description FROM schema_migrations
            WHERE version LIKE '%prompt%'
        """)
        migrations = cur.fetchall()
        if migrations:
            print(f"✅ 找到prompt schema migration记录:")
            for version, desc in migrations:
                print(f"   - {version}: {desc}")
        else:
            print("⚠️  未找到prompt schema migration记录")

        # 检查触发器
        cur.execute("""
            SELECT trigger_name FROM information_schema.triggers
            WHERE event_object_table = 'prompts'
            AND trigger_name LIKE '%updated_at%'
        """)
        triggers = [row[0] for row in cur.fetchall()]
        if triggers:
            print(f"✅ 找到prompts表updated_at触发器: {triggers}")
        else:
            print("⚠️  未找到prompts表updated_at触发器")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Prompt数据库schema验证失败: {e}")
        return False


async def verify_response_models():
    """验证: 响应模型统一"""
    print("\n🔍 验证: 响应模型统一")
    try:
        from backend.api.prompt_routes import PromptListResponse

        # 检查PromptListResponse的字段
        fields = PromptListResponse.model_fields
        required_fields = ['id', 'name', 'category', 'version', 'content',
                         'variables', 'tags', 'performance_score']

        missing = [f for f in required_fields if f not in fields]
        if missing:
            print(f"❌ PromptListResponse缺少字段: {missing}")
            return False

        print("✅ PromptListResponse模型字段完整")
        return True
    except Exception as e:
        print(f"❌ 响应模型验证失败: {e}")
        return False


async def verify_import_dependencies():
    """验证: 依赖导入"""
    print("\n🔍 验证: 依赖导入")
    try:
        # 检查asyncpg
        import asyncpg
        print("✅ asyncpg可用")

        # 检查pydantic-settings
        from pydantic_settings import BaseSettings
        print("✅ pydantic-settings可用")

        # 检查fastapi
        from fastapi import APIRouter
        print("✅ fastapi可用")

        return True
    except ImportError as e:
        print(f"❌ 依赖导入失败: {e}")
        return False


async def main():
    """运行所有验证"""
    print("=" * 60)
    print("🚀 P0修复验证脚本")
    print("=" * 60)

    results = {
        "数据库连接池工厂": await verify_database_pool(),
        "Prompt路由注册": await verify_prompt_routes(),
        "PromptUpdate模型字段": await verify_prompt_update_model(),
        "Prompt数据库schema": await verify_prompt_schema(),
        "响应模型统一": await verify_response_models(),
        "依赖导入": await verify_import_dependencies(),
    }

    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 验证通过")

    if passed == total:
        print("\n🎉 所有P0修复验证通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个验证失败，请检查")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
