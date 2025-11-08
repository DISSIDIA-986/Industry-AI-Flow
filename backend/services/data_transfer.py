"""数据文件传递服务 - 支持文件映射和数据库中转两种方式"""

import os
import uuid
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import create_engine, text
import tempfile
import shutil
import logging
from backend.config import settings

logger = logging.getLogger(__name__)


class DataFileTransferError(Exception):
    """数据文件传递异常"""
    pass


class DataFileTransfer:
    """数据文件传递服务"""

    def __init__(self):
        """初始化数据传递服务"""
        self.temp_dir = Path(settings.temp_data_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 数据库连接
        self.db_engine = None
        try:
            if settings.postgres_host and settings.postgres_db:
                self.db_engine = create_engine(settings.database_url)
                logger.info("数据库连接初始化成功")
        except Exception as e:
            logger.warning(f"数据库连接初始化失败: {e}")

    def transfer_file_for_docker(
        self,
        file_path: str,
        transfer_method: str = "auto"
    ) -> Dict[str, Any]:
        """
        为 Docker 环境传递数据文件

        Args:
            file_path: 原始文件路径
            transfer_method: 传递方式：'file_mapping', 'database', 'auto'

        Returns:
            传递结果字典，包含：
            - success: 是否成功
            - method: 使用的传递方式
            - transferred_path: 传递后的路径/表名
            - file_info: 文件信息
            - metadata: 元数据
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "method": transfer_method
            }

        try:
            # 获取文件信息
            file_info = self._get_file_info(file_path)

            # 选择传递方式
            if transfer_method == "auto":
                transfer_method = self._choose_transfer_method(file_info)

            if transfer_method == "file_mapping":
                return self._file_mapping_transfer(file_path, file_info)
            elif transfer_method == "database":
                return self._database_transfer(file_path, file_info)
            else:
                raise DataFileTransferError(f"不支持的传递方式: {transfer_method}")

        except Exception as e:
            logger.error(f"数据文件传递失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": transfer_method,
                "file_info": file_info
            }

    def _choose_transfer_method(self, file_info: Dict[str, Any]) -> str:
        """自动选择传递方式"""
        file_size = file_info.get("size_bytes", 0)

        # 小文件（<50MB）使用文件映射
        if file_size < 50 * 1024 * 1024:
            return "file_mapping"

        # 大文件或需要数据库操作的文件使用数据库中转
        if file_info.get("extension") in ['.csv', '.xlsx', '.xls', '.json', '.parquet']:
            return "database"

        # 默认使用文件映射
        return "file_mapping"

    def _file_mapping_transfer(self, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """文件映射传递方式"""
        try:
            # 创建临时文件目录
            temp_id = f"data_{uuid.uuid4().hex[:8]}"
            temp_dir = self.temp_dir / temp_id
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 复制文件到临时目录
            file_name = os.path.basename(file_path)
            temp_file_path = temp_dir / file_name

            shutil.copy2(file_path, temp_file_path)

            logger.info(f"文件映射传递完成: {file_path} -> {temp_file_path}")

            return {
                "success": True,
                "method": "file_mapping",
                "transferred_path": str(temp_file_path),
                "container_path": f"/workspace/data/{temp_id}/{file_name}",
                "temp_id": temp_id,
                "file_info": file_info,
                "metadata": {
                    "transfer_type": "file_mapping",
                    "cleanup_required": True,
                    "container_accessible": True
                }
            }

        except Exception as e:
            raise DataFileTransferError(f"文件映射传递失败: {e}")

    def _database_transfer(self, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """数据库中转传递方式"""
        if not self.db_engine:
            raise DataFileTransferError("数据库连接不可用")

        try:
            # 生成临时表名
            table_name = f"temp_data_{uuid.uuid4().hex[:8]}"

            # 根据文件类型读取数据
            df = self._read_file_to_dataframe(file_path, file_info)

            # 存储到数据库
            df.to_sql(
                table_name,
                con=self.db_engine,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=1000
            )

            # 创建连接配置文件
            config_id = f"db_config_{uuid.uuid4().hex[:8]}"
            config_content = self._create_db_config(table_name, file_info)

            config_file = self.temp_dir / f"{config_id}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(config_content, f, ensure_ascii=False, indent=2)

            logger.info(f"数据库中转传递完成: {file_path} -> {table_name}")

            return {
                "success": True,
                "method": "database",
                "transferred_path": table_name,
                "config_file": str(config_file),
                "config_id": config_id,
                "file_info": file_info,
                "metadata": {
                    "transfer_type": "database",
                    "table_name": table_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "cleanup_required": True
                }
            }

        except Exception as e:
            raise DataFileTransferError(f"数据库中转传递失败: {e}")

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        path = Path(file_path)
        stat = path.stat()

        return {
            "name": path.name,
            "path": str(path.absolute()),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": path.suffix.lower(),
            "modified_time": stat.st_mtime,
            "is_readable": os.access(file_path, os.R_OK)
        }

    def _read_file_to_dataframe(self, file_path: str, file_info: Dict[str, Any]) -> pd.DataFrame:
        """根据文件类型读取数据到 DataFrame"""
        extension = file_info["extension"]

        try:
            if extension == '.csv':
                # 自动检测编码和分隔符
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            elif extension in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif extension == '.json':
                df = pd.read_json(file_path, orient='records')
            elif extension == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                # 尝试以 CSV 格式读取
                logger.warning(f"不支持的文件类型 {extension}，尝试以 CSV 格式读取")
                df = pd.read_csv(file_path, encoding='utf-8-sig')

            # 基础数据清洗
            df = self._basic_data_cleaning(df)

            return df

        except Exception as e:
            raise DataFileTransferError(f"文件读取失败: {e}")

    def _basic_data_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础数据清洗"""
        # 复制数据避免修改原数据
        df_clean = df.copy()

        # 处理列名（去除前后空格，替换特殊字符）
        df_clean.columns = [
            str(col).strip().replace(' ', '_').replace('-', '_')
            for col in df_clean.columns
        ]

        # 去除完全重复的行
        df_clean.drop_duplicates(inplace=True)

        return df_clean

    def _create_db_config(self, table_name: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据库连接配置"""
        return {
            "connection": {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user or "current_user",
                "password": settings.postgres_password or ""
            },
            "table_info": {
                "table_name": table_name,
                "source_file": file_info["path"],
                "file_size": file_info["size_mb"],
                "transfer_timestamp": pd.Timestamp.now().isoformat()
            },
            "access_code_template": f"""
# 数据库访问代码
import pandas as pd
from sqlalchemy import create_engine

# 数据库连接
connection_string = "postgresql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(connection_string)

# 读取数据
df = pd.read_sql("SELECT * FROM {table_name}", engine)
print(f"数据形状: {{df.shape}}")
print("前5行:")
print(df.head())
""".format(
                user=settings.postgres_user or "current_user",
                password=settings.postgres_password or "",
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                table_name=table_name
            )
        }

    def create_container_access_script(
        self,
        transfer_result: Dict[str, Any],
        script_name: str = "access_data.py"
    ) -> str:
        """创建容器内数据访问脚本"""
        if transfer_result["method"] == "file_mapping":
            return self._create_file_access_script(transfer_result, script_name)
        elif transfer_result["method"] == "database":
            return self._create_database_access_script(transfer_result, script_name)
        else:
            raise DataFileTransferError(f"不支持的传递方式: {transfer_result['method']}")

    def _create_file_access_script(self, transfer_result: Dict[str, Any], script_name: str) -> str:
        """创建文件访问脚本"""
        container_path = transfer_result["container_path"]
        file_info = transfer_result["file_info"]

        script_content = f"""
# 数据访问脚本 - 文件映射方式
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 文件路径
data_path = "{container_path}"
file_name = "{file_info['name']}"
file_extension = "{file_info['extension']}"

# 检查文件是否存在
if not Path(data_path).exists():
    print(f"错误：数据文件不存在 - {{data_path}}")
    exit(1)

print(f"正在读取数据文件: {{file_name}}")

# 根据文件类型读取数据
try:
    if file_extension == '.csv':
        df = pd.read_csv(data_path, encoding='utf-8-sig')
    elif file_extension in ['.xlsx', '.xls']:
        df = pd.read_excel(data_path)
    elif file_extension == '.json':
        df = pd.read_json(data_path, orient='records')
    else:
        # 尝试以 CSV 格式读取
        df = pd.read_csv(data_path, encoding='utf-8-sig')

    print(f"数据读取成功！形状: {{df.shape}}")
    print("\\n数据信息:")
    print(df.info())
    print("\\n描述性统计:")
    print(df.describe())

    # 保存处理结果
    df.to_csv('/workspace/output/loaded_data.csv', index=False)
    print("\\n数据已保存到: /workspace/output/loaded_data.csv")

except Exception as e:
    print(f"数据读取失败: {{e}}")
    exit(1)
"""

        return script_content

    def _create_database_access_script(self, transfer_result: Dict[str, Any], script_name: str) -> str:
        """创建数据库访问脚本"""
        config_file = transfer_result["config_file"]
        table_name = transfer_result["transferred_path"]

        script_content = f"""
# 数据访问脚本 - 数据库中转方式
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import json
import os

# 读取数据库配置
config_path = "{config_file.replace(str(self.temp_dir), '/workspace/data')}"
if not Path(config_path).exists():
    print(f"错误：配置文件不存在 - {{config_path}}")
    exit(1)

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 数据库连接
    conn_info = config['connection']
    connection_string = (
        f"postgresql://{{conn_info['user']}}:{{conn_info['password']}}"
        f"@{{conn_info['host']}}:{{conn_info['port']}}/{{conn_info['database']}}"
    )

    engine = create_engine(connection_string)

    # 读取数据
    table_name = "{table_name}"
    print(f"正在从数据库表读取数据: {{table_name}}")

    df = pd.read_sql(f"SELECT * FROM {{table_name}}", engine)
    print(f"数据读取成功！形状: {{df.shape}}")

    print("\\n数据信息:")
    print(df.info())
    print("\\n描述性统计:")
    print(df.describe())

    # 保存处理结果
    df.to_csv('/workspace/output/loaded_data.csv', index=False)
    print("\\n数据已保存到: /workspace/output/loaded_data.csv")

    # 关闭数据库连接
    engine.dispose()

except Exception as e:
    print(f"数据库操作失败: {{e}}")
    exit(1)
"""

        return script_content

    def cleanup_transferred_data(self, transfer_result: Dict[str, Any]) -> bool:
        """清理传递的数据"""
        try:
            if transfer_result["method"] == "file_mapping":
                # 清理临时文件目录
                temp_id = transfer_result.get("temp_id")
                if temp_id:
                    temp_dir = self.temp_dir / temp_id
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
                        logger.info(f"已清理临时目录: {temp_dir}")

            elif transfer_result["method"] == "database":
                # 清理数据库临时表
                if self.db_engine:
                    table_name = transfer_result.get("transferred_path")
                    if table_name:
                        with self.db_engine.connect() as conn:
                            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                            conn.commit()
                            logger.info(f"已清理临时表: {table_name}")

                # 清理配置文件
                config_file = transfer_result.get("config_file")
                if config_file and os.path.exists(config_file):
                    os.remove(config_file)
                    logger.info(f"已清理配置文件: {config_file}")

            return True

        except Exception as e:
            logger.error(f"清理传递数据失败: {e}")
            return False


# 全局实例
data_transfer = DataFileTransfer()