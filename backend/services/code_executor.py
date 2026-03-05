"""Code Executor - Docker-based sandboxed Python code execution."""

import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from docker.errors import ContainerError, DockerException

import docker
from backend.config import settings

logger = logging.getLogger(__name__)


class CodeExecutionError(Exception):
    """Raised when code execution fails."""

    pass


class DockerCodeExecutor:
    """Docker-based sandboxed code executor."""

    def __init__(self):
        """Initialize Docker client and verify connection."""
        import threading as _threading

        try:
            self.client = docker.from_env()
            # Verify Docker daemon is reachable
            self.client.ping()
            logger.info("Docker client connected successfully")
        except DockerException as e:
            logger.error(f"Docker connection failed: {e}")
            raise CodeExecutionError(f"Docker connection failed: {e}")

        self._pending_cleanups: set[str] = set()
        self._cleanup_lock = _threading.Lock()
        self._cleanup_timer: Optional[_threading.Timer] = None

    def _prepare_workspace(self) -> str:
        """Create a temporary workspace directory for code execution."""
        workspace_id = f"workspace_{uuid.uuid4().hex[:8]}"
        workspace_path = Path(settings.temp_data_dir) / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return str(workspace_path)

    def _cleanup_workspace(self, workspace_path: str):
        """Remove a temporary workspace directory."""
        try:
            import shutil

            shutil.rmtree(workspace_path, ignore_errors=True)
            logger.info(f"Workspace cleaned up: {workspace_path}")
        except Exception as e:
            logger.warning(f"Workspace cleanup failed: {e}")

    def _schedule_cleanup(self, workspace_path: str) -> None:
        """Batch workspace cleanup using a single reusable timer."""
        import threading as _threading

        def _flush():
            with self._cleanup_lock:
                paths = list(self._pending_cleanups)
                self._pending_cleanups.clear()
                self._cleanup_timer = None
            for p in paths:
                self._cleanup_workspace(p)

        with self._cleanup_lock:
            self._pending_cleanups.add(workspace_path)
            if self._cleanup_timer is None:
                self._cleanup_timer = _threading.Timer(60.0, _flush)
                self._cleanup_timer.daemon = True
                self._cleanup_timer.start()

    def _validate_code(self, code: str) -> List[str]:
        """Validate code for security risks before execution."""
        import ast

        errors = []

        # Blacklisted dangerous operations
        blacklisted_operations = [
            "os.system",
            "subprocess.call",
            "eval",
            "exec",
            "__import__",
            "open",
            "file",
            "input",
            "raw_input",
            "execfile",
            "compile",
            "reload",
            "getattr",
        ]

        try:
            # Parse code into AST
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ["exec", "eval", "compile", "getattr", "setattr", "delattr", "__import__"]:
                            errors.append(f"Forbidden function call: {func_name}")
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            full_name = f"{node.func.value.id}.{node.func.attr}"
                            if any(op in full_name for op in blacklisted_operations):
                                errors.append(f"Forbidden operation: {full_name}")

                # Check for dangerous imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ["os", "subprocess", "sys", "importlib", "ctypes", "socket", "http", "requests", "urllib"]:
                            errors.append(f"Forbidden import: {alias.name}")

                if isinstance(node, ast.ImportFrom):
                    if node.module in ["os", "subprocess", "sys", "importlib", "ctypes", "socket", "http", "requests", "urllib"]:
                        errors.append(f"Forbidden import: {node.module}")

        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")

        return errors

    def execute_code(
        self,
        code: str,
        data_files: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code in a Docker container sandbox.

        Args:
            code: Python code to execute
            data_files: Optional list of data file paths to mount
            timeout: Execution timeout in seconds

        Returns:
            Dictionary containing execution results:
            - success: Whether execution succeeded
            - stdout: Standard output
            - stderr: Standard error
            - exit_code: Process exit code
            - execution_time: Execution duration in seconds
            - visualizations: List of generated visualization files
        """
        if timeout is None:
            timeout = settings.code_execution_timeout

        # Validate code security
        validation_errors = self._validate_code(code)
        if validation_errors:
            return {
                "success": False,
                "error": "Code validation failed.",
                "validation_errors": validation_errors,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "execution_time": 0,
                "visualizations": [],
            }

        # Prepare workspace
        workspace_path = self._prepare_workspace()

        try:
            # Write code to file
            code_file = Path(workspace_path) / "script.py"
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)

            # Set up volume mounts
            volumes = {workspace_path: {"bind": "/workspace", "mode": "rw"}}

            if data_files:
                for file_path in data_files:
                    if os.path.exists(file_path):
                        file_name = os.path.basename(file_path)
                        container_path = f"/workspace/data/{file_name}"
                        volumes[file_path] = {"bind": container_path, "mode": "ro"}

            # Build execution command
            command = ["python", "/workspace/script.py"]

            # Set resource limits
            mem_limit = settings.code_execution_memory_limit
            cpu_limit = float(settings.code_execution_cpu_limit)

            # Record start time
            start_time = time.time()

            try:
                container = self.client.containers.run(
                    image=settings.docker_image_name,
                    command=command,
                    volumes=volumes,
                    mem_limit=mem_limit,
                    cpu_quota=int(cpu_limit * 100000),  # Docker CPU quota
                    cpu_period=100000,
                    network_mode="none",  # Disable network access
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True,
                    user="1000:1000",  # Run as non-root user
                    timeout=timeout,
                )

                execution_time = time.time() - start_time

                # Parse output
                stdout = (
                    container.decode("utf-8")
                    if isinstance(container, bytes)
                    else str(container)
                )
                stderr = ""
                exit_code = 0

                # If container object has logs, extract them
                if hasattr(container, "logs"):
                    try:
                        logs = container.logs(stdout=True, stderr=True)
                        stdout = logs.decode("utf-8")
                    except:
                        pass

                # Find generated visualization files
                visualizations = self._find_visualization_files(workspace_path)

                return {
                    "success": True,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "execution_time": execution_time,
                    "visualizations": visualizations,
                    "workspace_id": os.path.basename(workspace_path),
                }

            except ContainerError as e:
                execution_time = time.time() - start_time
                return {
                    "success": False,
                    "error": "Code execution failed.",
                    "stdout": e.stdout.decode("utf-8") if e.stdout else "",
                    "stderr": e.stderr.decode("utf-8") if e.stderr else str(e),
                    "exit_code": e.exit_status,
                    "execution_time": execution_time,
                    "visualizations": [],
                    "workspace_id": os.path.basename(workspace_path),
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Execution timed out after {timeout} seconds.",
                    "stdout": "",
                    "stderr": "Execution timeout",
                    "exit_code": -1,
                    "execution_time": timeout,
                    "visualizations": [],
                    "workspace_id": os.path.basename(workspace_path),
                }

        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return {
                "success": False,
                "error": f"Code execution service error: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "execution_time": 0,
                "visualizations": [],
                "workspace_id": os.path.basename(workspace_path),
            }

        finally:
            # Schedule workspace cleanup without spawning a thread per call.
            # Paths are batched and cleaned by a single reusable timer.
            self._schedule_cleanup(workspace_path)

    def _find_visualization_files(self, workspace_path: str) -> List[Dict[str, str]]:
        """Find generated visualization files in the workspace."""
        visualizations = []
        workspace = Path(workspace_path)

        # Supported visualization file extensions
        viz_extensions = [".png", ".jpg", ".jpeg", ".svg", ".html", ".pdf", ".gif", ".webp"]

        for file_path in workspace.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in viz_extensions:
                # Read text-based visualizations inline
                content = None
                if file_path.suffix.lower() in [".html", ".svg"]:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except:
                        pass

                visualizations.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "type": file_path.suffix.lower()[1:],  # Remove leading dot
                        "size": file_path.stat().st_size,
                        "content": content,
                    }
                )

        return visualizations


# Lazy initialization: avoid blocking import when Docker is unavailable.
_code_executor = None


def get_code_executor():
    global _code_executor
    if _code_executor is None:
        try:
            instance = DockerCodeExecutor()
            _code_executor = instance
        except (CodeExecutionError, Exception) as exc:
            logger.warning("Docker unavailable for code execution: %s", exc)
            _code_executor = None
    return _code_executor


# Backward-compatible alias; prefer get_code_executor() for lazy init.
code_executor = None
