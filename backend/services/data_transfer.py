"""Data File Transfer - Transfers data files for Docker container access."""

import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
try:
    from sqlalchemy import create_engine, text
except Exception:  # pragma: no cover - optional dependency
    create_engine = None  # type: ignore[assignment]
    text = None  # type: ignore[assignment]

from backend.config import settings

logger = logging.getLogger(__name__)


class DataFileTransferError(Exception):
    """Exception raised when data file transfer fails."""

    pass


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_source_roots() -> list[Path]:
    roots = [
        Path.cwd().resolve(),
        Path(settings.temp_data_dir).resolve(),
        Path(os.getenv("TMPDIR", "/tmp")).resolve(),
        Path("/tmp").resolve(),
    ]
    seen: set[Path] = set()
    unique_roots: list[Path] = []
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        unique_roots.append(root)
    return unique_roots


def _resolve_allowed_source_file(file_path: str) -> Path:
    candidate = Path(file_path).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed_roots = _allowed_source_roots()
    if not any(_is_subpath(candidate, root) or candidate == root for root in allowed_roots):
        raise DataFileTransferError("Path outside allowed directories")

    if not candidate.exists():
        raise DataFileTransferError(f"File not found: {candidate}")
    if not candidate.is_file():
        raise DataFileTransferError(f"Not a regular file: {candidate}")
    if not os.access(candidate, os.R_OK):
        raise DataFileTransferError(f"File not readable: {candidate}")

    return candidate


class DataFileTransfer:
    """Handles transferring user data files to Docker containers via file mapping or database."""

    def __init__(self):
        """Initialize the data file transfer service."""
        self.temp_dir = Path(settings.temp_data_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Database engine for database transfer method
        self.db_engine = None
        try:
            if create_engine and settings.postgres_host and settings.postgres_db:
                self.db_engine = create_engine(settings.database_url)
                logger.info("Database engine initialized for data transfer")
        except Exception as e:
            logger.warning(f"Database engine initialization failed: {e}")

    def transfer_file_for_docker(
        self, file_path: str, transfer_method: str = "auto"
    ) -> Dict[str, Any]:
        """
        Transfer a data file for Docker container access.

        Args:
            file_path: Path to the source data file.
            transfer_method: Transfer method: 'file_mapping', 'database', or 'auto'.

        Returns:
            Transfer result dictionary containing:
            - success: Whether transfer succeeded.
            - method: Transfer method used.
            - transferred_path: Path or table name in target environment.
            - file_info: File metadata.
            - metadata: Additional transfer metadata.
        """
        file_info: Optional[Dict[str, Any]] = None

        try:
            safe_file_path = _resolve_allowed_source_file(file_path)

            # Get file metadata
            file_info = self._get_file_info(str(safe_file_path))

            # Auto-select transfer method if needed
            if transfer_method == "auto":
                transfer_method = self._choose_transfer_method(file_info)

            if transfer_method == "file_mapping":
                return self._file_mapping_transfer(str(safe_file_path), file_info)
            elif transfer_method == "database":
                return self._database_transfer(str(safe_file_path), file_info)
            else:
                raise DataFileTransferError(f"Unsupported transfer method: {transfer_method}")

        except Exception as e:
            logger.error(f"File transfer failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": transfer_method,
                "file_info": file_info,
            }

    def _choose_transfer_method(self, file_info: Dict[str, Any]) -> str:
        """Choose the optimal transfer method based on file size and type."""
        file_size = file_info.get("size_bytes", 0)

        # Small files (<50MB) use file mapping
        if file_size < 50 * 1024 * 1024:
            return "file_mapping"

        # Structured data formats use database transfer
        if file_info.get("extension") in [".csv", ".xlsx", ".xls", ".json", ".parquet"]:
            return "database"

        # Default to file mapping
        return "file_mapping"

    def _file_mapping_transfer(
        self, file_path: str, file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transfer a file via file system mapping (copy to temp directory)."""
        try:
            # Create temporary directory for this transfer
            temp_id = f"data_{uuid.uuid4().hex[:8]}"
            temp_dir = self.temp_dir / temp_id
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Copy file to temp location
            file_name = os.path.basename(file_path)
            temp_file_path = temp_dir / file_name

            shutil.copy2(file_path, temp_file_path)

            logger.info(f"File mapped: {file_path} -> {temp_file_path}")

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
                    "container_accessible": True,
                },
            }

        except Exception as e:
            raise DataFileTransferError(f"Data transfer failed: {e}")

    def _database_transfer(
        self, file_path: str, file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transfer data to the database as a temporary table."""
        if not self.db_engine:
            raise DataFileTransferError("Database engine not available for data transfer")

        try:
            # Create temporary table name
            table_name = f"temp_data_{uuid.uuid4().hex[:8]}"

            # Read file into DataFrame
            df = self._read_file_to_dataframe(file_path, file_info)

            # Write to database
            df.to_sql(
                table_name,
                con=self.db_engine,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=1000,
            )

            # Generate database access config file
            config_id = f"db_config_{uuid.uuid4().hex[:8]}"
            config_content = self._create_db_config(table_name, file_info)

            config_file = self.temp_dir / f"{config_id}.json"
            with open(config_file, "w", encoding="utf-8") as f:
                import json

                json.dump(config_content, f, ensure_ascii=False, indent=2)

            logger.info(f"Database transfer complete: {file_path} -> {table_name}")

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
                    "cleanup_required": True,
                },
            }

        except Exception as e:
            raise DataFileTransferError(f"Data transfer failed: {e}")

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file metadata information."""
        path = Path(file_path)
        stat = path.stat()

        return {
            "name": path.name,
            "path": str(path.absolute()),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": path.suffix.lower(),
            "modified_time": stat.st_mtime,
            "is_readable": os.access(file_path, os.R_OK),
        }

    def _read_file_to_dataframe(
        self, file_path: str, file_info: Dict[str, Any]
    ) -> pd.DataFrame:
        """Read a file into a pandas DataFrame."""
        extension = file_info["extension"]

        try:
            if extension == ".csv":
                # Auto-detect encoding with BOM support
                df = pd.read_csv(file_path, encoding="utf-8-sig")
            elif extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path)
            elif extension == ".json":
                df = pd.read_json(file_path, orient="records")
            elif extension == ".parquet":
                df = pd.read_parquet(file_path)
            else:
                # Unknown format, attempt CSV parsing as fallback
                logger.warning(f"Unknown extension {extension}, attempting CSV parsing")
                df = pd.read_csv(file_path, encoding="utf-8-sig")

            # Basic data cleaning
            df = self._basic_data_cleaning(df)

            return df

        except Exception as e:
            raise DataFileTransferError(f"Data transfer failed: {e}")

    def _basic_data_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """Perform basic data cleaning on a DataFrame."""
        # Work on a copy
        df_clean = df.copy()

        # Normalize column names (strip whitespace, replace spaces/hyphens with underscores)
        df_clean.columns = [
            str(col).strip().replace(" ", "_").replace("-", "_")
            for col in df_clean.columns
        ]

        # Remove duplicate rows
        df_clean.drop_duplicates(inplace=True)

        return df_clean

    def _create_db_config(
        self, table_name: str, file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a database access configuration file for the container."""
        return {
            "connection": {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user or "current_user",
                "password_env": "POSTGRES_PASSWORD",
            },
            "table_info": {
                "table_name": table_name,
                "source_file": file_info["path"],
                "file_size": file_info["size_mb"],
                "transfer_timestamp": pd.Timestamp.now().isoformat(),
            },
            "access_code_template": (
                "# Database access template\n"
                "import os\n"
                "import pandas as pd\n"
                "from sqlalchemy import create_engine\n"
                "\n"
                "# Read credentials from env\n"
                f"connection_string = \"postgresql://{settings.postgres_user or 'current_user'}"
                f":\" + os.environ.get('POSTGRES_PASSWORD', '') + \""
                f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}\"\n"
                "engine = create_engine(connection_string)\n"
                "\n"
                f"df = pd.read_sql(\"SELECT * FROM {table_name}\", engine)\n"
                "print(f\"Loaded: {df.shape}\")\n"
                "print(df.head())\n"
            ),
        }

    def create_container_access_script(
        self, transfer_result: Dict[str, Any], script_name: str = "access_data.py"
    ) -> str:
        """Generate a Python script for accessing transferred data inside the container."""
        if transfer_result["method"] == "file_mapping":
            return self._create_file_access_script(transfer_result, script_name)
        elif transfer_result["method"] == "database":
            return self._create_database_access_script(transfer_result, script_name)
        else:
            raise DataFileTransferError(f"Unsupported transfer method: {transfer_result['method']}")

    def _create_file_access_script(
        self, transfer_result: Dict[str, Any], script_name: str
    ) -> str:
        """Generate a file-based data access script for the container."""
        container_path = transfer_result["container_path"]
        file_info = transfer_result["file_info"]

        script_content = f"""
# Auto-generated data access script - File mapping method
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Data file configuration
data_path = "{container_path}"
file_name = "{file_info['name']}"
file_extension = "{file_info['extension']}"

# Verify file exists
if not Path(data_path).exists():
    print(f"Error: File not found - {{data_path}}")
    exit(1)

print(f"Loading file: {{file_name}}")

# Load data
try:
    if file_extension == '.csv':
        df = pd.read_csv(data_path, encoding='utf-8-sig')
    elif file_extension in ['.xlsx', '.xls']:
        df = pd.read_excel(data_path)
    elif file_extension == '.json':
        df = pd.read_json(data_path, orient='records')
    else:
        # Fallback: attempt CSV parsing
        df = pd.read_csv(data_path, encoding='utf-8-sig')

    print(f"Loaded successfully! Shape: {{df.shape}}")
    print("\\nData info:")
    print(df.info())
    print("\\nStatistics:")
    print(df.describe())

    # Save processed data
    df.to_csv('/workspace/output/loaded_data.csv', index=False)
    print("\\nSaved to: /workspace/output/loaded_data.csv")

except Exception as e:
    print(f"Error loading data: {{e}}")
    exit(1)
"""

        return script_content

    def _create_database_access_script(
        self, transfer_result: Dict[str, Any], script_name: str
    ) -> str:
        """Generate a database-based data access script for the container."""
        config_file = transfer_result["config_file"]
        table_name = transfer_result["transferred_path"]

        script_content = f"""
# Auto-generated data access script - Database method
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import json
import os

# Load database configuration
config_path = "{config_file.replace(str(self.temp_dir), '/workspace/data')}"
if not Path(config_path).exists():
    print(f"Error: Config not found - {{config_path}}")
    exit(1)

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Build connection string
    conn_info = config['connection']
    connection_string = (
        f"postgresql://{{conn_info['user']}}:{{conn_info['password']}}"
        f"@{{conn_info['host']}}:{{conn_info['port']}}/{{conn_info['database']}}"
    )

    engine = create_engine(connection_string)

    # Load data from table
    table_name = "{table_name}"
    print(f"Loading table: {{table_name}}")

    df = pd.read_sql(f"SELECT * FROM {{table_name}}", engine)
    print(f"Loaded successfully! Shape: {{df.shape}}")

    print("\\nData info:")
    print(df.info())
    print("\\nStatistics:")
    print(df.describe())

    # Save processed data
    df.to_csv('/workspace/output/loaded_data.csv', index=False)
    print("\\nSaved to: /workspace/output/loaded_data.csv")

    # Clean up connection
    engine.dispose()

except Exception as e:
    print(f"Error loading data: {{e}}")
    exit(1)
"""

        return script_content

    def cleanup_transferred_data(self, transfer_result: Dict[str, Any]) -> bool:
        """Clean up transferred data (temp files or temp database tables)."""
        try:
            if transfer_result["method"] == "file_mapping":
                # Remove temporary directory
                temp_id = transfer_result.get("temp_id")
                if temp_id:
                    temp_dir = self.temp_dir / temp_id
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
                        logger.info(f"Cleaned up temp directory: {temp_dir}")

            elif transfer_result["method"] == "database":
                # Drop temporary table
                if self.db_engine and text is not None:
                    table_name = transfer_result.get("transferred_path")
                    if table_name and re.match(r"^temp_data_[0-9a-f]{8}$", table_name):
                        with self.db_engine.connect() as conn:
                            conn.execute(
                                text("DROP TABLE IF EXISTS " + table_name)
                            )
                            conn.commit()
                            logger.info(f"Dropped temp table: {table_name}")
                    elif table_name:
                        logger.warning(
                            "Refused to drop table with unexpected name: %s",
                            table_name,
                        )

                # Remove config file
                config_file = transfer_result.get("config_file")
                if config_file and os.path.exists(config_file):
                    os.remove(config_file)
                    logger.info(f"Removed config file: {config_file}")

            return True

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False


# Global data transfer instance
data_transfer = DataFileTransfer()
