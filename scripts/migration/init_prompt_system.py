#!/usr/bin/env python3
"""
Prompt管理系统初始化脚本
设置数据库、创建表结构、导入基础数据
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg

from backend.config import get_database_url

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 连接到默认数据库
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            database="postgres",  # 默认数据库
        )

        # 创建应用数据库
        await conn.execute(
            """
            CREATE DATABASE industry_ai_flow_prompts
            WITH
            OWNER = postgres
            ENCODING = 'UTF8'
            LC_COLLATE = 'en_US.UTF-8'
            LC_CTYPE = 'en_US.UTF-8'
            TABLESPACE = pg_default
            CONNECTION LIMIT = -1;
        """
        )

        await conn.close()
        logger.info("✅ 数据库创建成功")
        return True

    except Exception as e:
        if "already exists" in str(e):
            logger.info("✅ 数据库已存在")
            return True
        else:
            logger.error(f"❌ 数据库创建失败: {e}")
            return False


async def execute_migration():
    """执行数据库迁移"""
    try:
        # 连接到应用数据库
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            database="industry_ai_flow_prompts",
        )

        # 读取迁移文件
        migration_file = (
            project_root / "backend" / "migrations" / "001_create_prompt_tables.sql"
        )

        if not migration_file.exists():
            logger.error(f"❌ 迁移文件不存在: {migration_file}")
            return False

        with open(migration_file, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # 执行迁移
        await conn.execute(migration_sql)
        await conn.close()

        logger.info("✅ 数据库迁移成功")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}")
        return False


async def test_system():
    """测试Prompt管理系统"""
    try:
        # 导入并测试Prompt管理器
        from backend.services.prompt_manager import PromptManager, PromptVariable

        # 获取数据库连接池
        pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            database="industry_ai_flow_prompts",
            min_size=5,
            max_size=20,
        )

        # 初始化Prompt管理器
        prompt_manager = PromptManager(pool)

        # 测试创建Prompt
        test_prompt = await prompt_manager.create_prompt(
            name="test_prompt",
            category="Test",
            content="这是一个测试Prompt，变量：{{test_var}}",
            variables=[
                PromptVariable(
                    name="test_var", type="string", required=True, description="测试变量"
                )
            ],
            tags=["test"],
            created_by="init_script",
        )

        logger.info(f"✅ 测试Prompt创建成功: {test_prompt.id}")

        # 测试获取和渲染Prompt
        prompt_info, rendered_content = await prompt_manager.get_prompt(
            name="test_prompt", category="Test", variables={"test_var": "Hello World"}
        )

        logger.info(f"✅ Prompt渲染成功: {rendered_content}")

        # 测试性能统计
        performance = await prompt_manager.get_prompt_performance(test_prompt.id)
        logger.info(f"✅ 性能统计获取成功: {performance}")

        # 清理测试数据
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM prompts WHERE name = 'test_prompt' AND category = 'Test'"
            )

        await pool.close()
        logger.info("✅ 系统测试完成")
        return True

    except Exception as e:
        logger.error(f"❌ 系统测试失败: {e}")
        return False


async def run_migration_script():
    """运行Prompt迁移脚本"""
    try:
        # 导入迁移脚本
        sys.path.append(str(project_root / "scripts"))
        from migrate_existing_prompts import main as migrate_main

        logger.info("🚀 开始运行Prompt迁移脚本")

        # 执行迁移
        exit_code = await migrate_main()

        if exit_code == 0:
            logger.info("✅ Prompt迁移完成")
            return True
        else:
            logger.error("❌ Prompt迁移失败")
            return False

    except Exception as e:
        logger.error(f"❌ 迁移脚本执行失败: {e}")
        return False


async def main():
    """主初始化流程"""
    print("🎯 Prompt管理系统初始化")
    print("=" * 50)

    steps = [
        ("创建数据库", create_database),
        ("执行数据库迁移", execute_migration),
        ("测试系统功能", test_system),
        ("迁移现有Prompt", run_migration_script),
    ]

    success_count = 0

    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            if await step_func():
                success_count += 1
                print(f"✅ {step_name} 完成")
            else:
                print(f"❌ {step_name} 失败")
        except Exception as e:
            print(f"❌ {step_name} 异常: {e}")

    print("\n" + "=" * 50)
    print(f"🎉 初始化完成: {success_count}/{len(steps)} 个步骤成功")

    if success_count == len(steps):
        print("\n🚀 Prompt管理系统已就绪!")
        print("\n下一步操作:")
        print("1. 启动API服务: uvicorn backend.main:app --reload")
        print("2. 启动Web界面: streamlit run streamlit_prompt_manager.py")
        print("3. 访问Prompt管理平台")
        return 0
    else:
        print(f"\n⚠️ 还有 {len(steps) - success_count} 个步骤需要处理")
        return 1


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
