"""
Docker-based Python code executor with security constraints.

Features:
- Network isolation
- Resource limits (CPU, memory, timeout)
- Non-root user execution
- File system isolation
- Result extraction (stdout, files, plots)
"""

import io
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from docker.errors import APIError, ContainerError, ImageNotFound
from docker.types import DeviceRequest

import docker


@dataclass
class ExecutionResult:
    """Code execution result."""

    success: bool
    stdout: str
    stderr: str
    error: Optional[str] = None
    execution_time: float = 0.0
    output_files: dict[str, bytes] = None  # filename -> content

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = {}


logger = logging.getLogger(__name__)


class DockerExecutor:
    """
    Secure Python code executor using Docker containers.

    Security features:
    - Network disabled by default
    - CPU and memory limits enforced
    - Execution timeout control
    - Non-root user (UID 1000)
    - Read-only file system except /workspace
    """

    # Docker image configuration
    IMAGE_NAME = "industry-ai-flow/data-analysis"
    IMAGE_TAG = "latest"

    # Resource limits
    DEFAULT_TIMEOUT = 60  # seconds
    DEFAULT_MEM_LIMIT = "512m"
    DEFAULT_CPU_QUOTA = 50000  # 0.5 CPU

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        mem_limit: str = DEFAULT_MEM_LIMIT,
        cpu_quota: int = DEFAULT_CPU_QUOTA,
        enable_network: bool = False,
    ):
        """
        Initialize Docker executor.

        Args:
            timeout: Maximum execution time in seconds
            mem_limit: Memory limit (e.g., "512m", "1g")
            cpu_quota: CPU quota (100000 = 1 CPU)
            enable_network: Whether to enable network access
        """
        self.timeout = timeout
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.enable_network = enable_network

        try:
            self.client = docker.from_env()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

        # Ensure image exists
        self._ensure_image()

    def _ensure_image(self) -> None:
        """Build Docker image if it doesn't exist."""
        try:
            self.client.images.get(f"{self.IMAGE_NAME}:{self.IMAGE_TAG}")
        except ImageNotFound:
            logger.info("Building Docker image %s:%s", self.IMAGE_NAME, self.IMAGE_TAG)
            dockerfile_path = (
                Path(__file__).parent.parent.parent.parent / "docker" / "data-analysis"
            )

            if not dockerfile_path.exists():
                raise FileNotFoundError(f"Dockerfile not found at {dockerfile_path}")

            try:
                self.client.images.build(
                    path=str(dockerfile_path),
                    tag=f"{self.IMAGE_NAME}:{self.IMAGE_TAG}",
                    rm=True,
                )
                logger.info(
                    "Successfully built Docker image %s:%s",
                    self.IMAGE_NAME,
                    self.IMAGE_TAG,
                )
            except Exception as e:
                raise RuntimeError(f"Failed to build Docker image: {e}")

    def execute(
        self,
        code: str,
        input_files: Optional[dict[str, bytes]] = None,
    ) -> ExecutionResult:
        """
        Execute Python code in isolated Docker container.

        Args:
            code: Python code to execute
            input_files: Optional input files (filename -> content)

        Returns:
            ExecutionResult with stdout, stderr, and output files
        """
        start_time = time.time()

        # Create temporary directory for file exchange
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Write code to file
            code_file = workspace / "main.py"
            code_file.write_text(code, encoding="utf-8")

            # Write input files
            if input_files:
                for filename, content in input_files.items():
                    file_path = workspace / filename
                    file_path.write_bytes(content)

            try:
                # Run container
                result = self._run_container(workspace)

                # Collect output files (excluding main.py)
                output_files = {}
                for file_path in workspace.iterdir():
                    if file_path.name != "main.py" and file_path.is_file():
                        output_files[file_path.name] = file_path.read_bytes()

                execution_time = time.time() - start_time

                return ExecutionResult(
                    success=True,
                    stdout=result["stdout"],
                    stderr=result["stderr"],
                    execution_time=execution_time,
                    output_files=output_files,
                )

            except ContainerError as e:
                execution_time = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=e.stderr.decode("utf-8") if e.stderr else "",
                    error=f"Container execution failed: {e}",
                    execution_time=execution_time,
                )

            except Exception as e:
                execution_time = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    error=f"Execution error: {str(e)}",
                    execution_time=execution_time,
                )

    def _run_container(self, workspace: Path) -> dict:
        """Run Docker container with security constraints."""
        container = None
        try:
            # Container configuration
            container_config = {
                "image": f"{self.IMAGE_NAME}:{self.IMAGE_TAG}",
                "command": ["python", "/workspace/main.py"],
                "working_dir": "/workspace",
                "volumes": {
                    str(workspace.absolute()): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                "mem_limit": self.mem_limit,
                "cpu_quota": self.cpu_quota,
                "network_disabled": not self.enable_network,
                "user": "1000:1000",  # Non-root user
                "read_only": True,
                "tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},
                "security_opt": ["no-new-privileges"],
                "detach": True,
                "remove": False,  # Keep container for log extraction
            }

            # Create and start container
            container = self.client.containers.run(**container_config)

            # Wait for completion with timeout
            exit_status = container.wait(timeout=self.timeout)

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

            # Check exit status
            if exit_status["StatusCode"] != 0:
                raise ContainerError(
                    container=container,
                    exit_status=exit_status["StatusCode"],
                    command="python /workspace/main.py",
                    image=f"{self.IMAGE_NAME}:{self.IMAGE_TAG}",
                    stderr=stderr.encode("utf-8"),
                )

            return {
                "stdout": stdout,
                "stderr": stderr,
            }

        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass  # Ignore cleanup errors

    def execute_code(
        self,
        code: str,
        data_files: Optional[list[str]] = None,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        执行代码（兼容旧接口）

        Args:
            code: Python代码
            data_files: 数据文件路径列表
            timeout: 超时时间（秒）

        Returns:
            执行结果字典
        """
        # 覆盖超时时间（如果提供）
        old_timeout = self.timeout
        if timeout is not None:
            self.timeout = timeout

        try:
            # 读取数据文件
            input_files = {}
            if data_files:
                for file_path in data_files:
                    try:
                        with open(file_path, "rb") as f:
                            input_files[Path(file_path).name] = f.read()
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"无法读取数据文件 {file_path}: {e}",
                            "stdout": "",
                            "stderr": "",
                            "exit_code": -1,
                            "execution_time": 0,
                            "visualizations": [],
                        }

            # 执行代码
            result = self.execute(code, input_files)

            # 转换为旧格式
            visualizations = [
                name
                for name in result.output_files.keys()
                if name.endswith((".png", ".jpg", ".svg", ".pdf", ".html"))
            ]

            return {
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "exit_code": 0 if result.success else 1,
                "execution_time": result.execution_time,
                "visualizations": visualizations,
                "output_files": result.output_files,
            }

        finally:
            # 恢复原超时时间
            self.timeout = old_timeout

    def _validate_code(self, code: str) -> list[str]:
        """
        验证代码（兼容旧接口）

        Args:
            code: Python代码

        Returns:
            错误列表（空列表表示通过验证）
        """
        from backend.services.code_executor.validator import validate_code

        validation_result = validate_code(code, strict_mode=True)

        if validation_result.is_valid:
            return []

        errors = []
        if validation_result.error:
            errors.append(validation_result.error)
        errors.extend(validation_result.warnings)

        return errors

    def close(self):
        """Close Docker client connection."""
        if hasattr(self, "client"):
            self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function
def execute_python_code(
    code: str,
    input_files: Optional[dict[str, bytes]] = None,
    timeout: int = DockerExecutor.DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """
    Execute Python code in Docker sandbox (convenience function).

    Args:
        code: Python code to execute
        input_files: Optional input files
        timeout: Maximum execution time in seconds

    Returns:
        ExecutionResult
    """
    with DockerExecutor(timeout=timeout) as executor:
        return executor.execute(code, input_files)
