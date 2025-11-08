"""代码执行服务 - Docker 沙箱环境"""

import os
import uuid
import tempfile
import subprocess
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import docker
from docker.errors import DockerException, ContainerError
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class CodeExecutionError(Exception):
    """代码执行异常"""
    pass


class DockerCodeExecutor:
    """Docker 沙箱代码执行器"""
    
    def __init__(self):
        """初始化 Docker 客户端"""
        try:
            self.client = docker.from_env()
            # 测试 Docker 连接
            self.client.ping()
            logger.info("Docker 客户端连接成功")
        except DockerException as e:
            logger.error(f"Docker 连接失败: {e}")
            raise CodeExecutionError(f"Docker 不可用: {e}")
    
    def _prepare_workspace(self) -> str:
        """准备临时工作空间"""
        workspace_id = f"workspace_{uuid.uuid4().hex[:8]}"
        workspace_path = Path(settings.temp_data_dir) / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return str(workspace_path)
    
    def _cleanup_workspace(self, workspace_path: str):
        """清理临时工作空间"""
        try:
            import shutil
            shutil.rmtree(workspace_path, ignore_errors=True)
            logger.info(f"清理工作空间: {workspace_path}")
        except Exception as e:
            logger.warning(f"清理工作空间失败: {e}")
    
    def _validate_code(self, code: str) -> List[str]:
        """代码安全检查"""
        import ast
        
        errors = []
        
        # 危险操作黑名单
        blacklisted_operations = [
            'os.system', 'subprocess.call', 'eval', 'exec',
            '__import__', 'open', 'file', 'input', 'raw_input',
            'execfile', 'compile', 'reload'
        ]
        
        try:
            # AST 解析检查
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # 检查函数调用
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ['exec', 'eval', 'compile']:
                            errors.append(f"禁止使用函数: {func_name}")
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            full_name = f"{node.func.value.id}.{node.func.attr}"
                            if any(op in full_name for op in blacklisted_operations):
                                errors.append(f"禁止使用操作: {full_name}")
                
                # 检查导入语句
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ['os', 'subprocess', 'sys']:
                            errors.append(f"禁止导入模块: {alias.name}")
                
                if isinstance(node, ast.ImportFrom):
                    if node.module in ['os', 'subprocess', 'sys']:
                        errors.append(f"禁止从模块导入: {node.module}")
        
        except SyntaxError as e:
            errors.append(f"语法错误: {e}")
        
        return errors
    
    def execute_code(
        self,
        code: str,
        data_files: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        在 Docker 沙箱中执行 Python 代码
        
        Args:
            code: 要执行的 Python 代码
            data_files: 数据文件路径列表
            timeout: 执行超时时间（秒）
            
        Returns:
            执行结果字典，包含:
            - success: 是否成功
            - stdout: 标准输出
            - stderr: 标准错误
            - exit_code: 退出码
            - execution_time: 执行时间
            - visualizations: 生成的可视化文件列表
        """
        if timeout is None:
            timeout = settings.code_execution_timeout
        
        # 代码安全检查
        validation_errors = self._validate_code(code)
        if validation_errors:
            return {
                "success": False,
                "error": "代码安全检查失败",
                "validation_errors": validation_errors,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "execution_time": 0,
                "visualizations": []
            }
        
        # 准备工作空间
        workspace_path = self._prepare_workspace()
        
        try:
            # 写入代码文件
            code_file = Path(workspace_path) / "script.py"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 准备数据文件映射
            volumes = {workspace_path: {"bind": "/workspace", "mode": "rw"}}
            
            if data_files:
                for file_path in data_files:
                    if os.path.exists(file_path):
                        file_name = os.path.basename(file_path)
                        container_path = f"/workspace/data/{file_name}"
                        volumes[file_path] = {"bind": container_path, "mode": "ro"}
            
            # 准备执行命令
            command = [
                "python", "/workspace/script.py"
            ]
            
            # 资源限制
            mem_limit = settings.code_execution_memory_limit
            cpu_limit = float(settings.code_execution_cpu_limit)
            
            # 执行容器
            start_time = time.time()
            
            try:
                container = self.client.containers.run(
                    image=settings.docker_image_name,
                    command=command,
                    volumes=volumes,
                    mem_limit=mem_limit,
                    cpu_quota=int(cpu_limit * 100000),  # Docker CPU quota
                    cpu_period=100000,
                    network_mode="none",  # 禁用网络访问
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True,
                    user="1000:1000"  # 非root用户
                )
                
                execution_time = time.time() - start_time
                
                # 解析输出
                stdout = container.decode('utf-8') if isinstance(container, bytes) else str(container)
                stderr = ""
                exit_code = 0
                
                # 如果是容器对象，获取输出
                if hasattr(container, 'logs'):
                    try:
                        logs = container.logs(stdout=True, stderr=True)
                        stdout = logs.decode('utf-8')
                    except:
                        pass
                
                # 检查生成的可视化文件
                visualizations = self._find_visualization_files(workspace_path)
                
                return {
                    "success": True,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "execution_time": execution_time,
                    "visualizations": visualizations,
                    "workspace_path": workspace_path
                }
                
            except ContainerError as e:
                execution_time = time.time() - start_time
                return {
                    "success": False,
                    "error": "容器执行错误",
                    "stdout": e.stdout.decode('utf-8') if e.stdout else "",
                    "stderr": e.stderr.decode('utf-8') if e.stderr else str(e),
                    "exit_code": e.exit_status,
                    "execution_time": execution_time,
                    "visualizations": [],
                    "workspace_path": workspace_path
                }
            
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"代码执行超时（{timeout}秒）",
                    "stdout": "",
                    "stderr": "Execution timeout",
                    "exit_code": -1,
                    "execution_time": timeout,
                    "visualizations": [],
                    "workspace_path": workspace_path
                }
        
        except Exception as e:
            logger.error(f"代码执行异常: {e}")
            return {
                "success": False,
                "error": f"执行异常: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "execution_time": 0,
                "visualizations": [],
                "workspace_path": workspace_path
            }
        
        finally:
            # 延迟清理工作空间（给API调用时间获取结果）
            import threading
            def cleanup_later():
                time.sleep(60)  # 60秒后清理
                self._cleanup_workspace(workspace_path)
            
            cleanup_thread = threading.Thread(target=cleanup_later)
            cleanup_thread.daemon = True
            cleanup_thread.start()
    
    def _find_visualization_files(self, workspace_path: str) -> List[Dict[str, str]]:
        """查找生成的可视化文件"""
        visualizations = []
        workspace = Path(workspace_path)
        
        # 支持的可视化文件格式
        viz_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.html', '.pdf']
        
        for file_path in workspace.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in viz_extensions:
                # 读取文件内容（如果是文本文件）
                content = None
                if file_path.suffix.lower() in ['.html', '.svg']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except:
                        pass
                
                visualizations.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "type": file_path.suffix.lower()[1:],  # 去掉点号
                    "size": file_path.stat().st_size,
                    "content": content
                })
        
        return visualizations


# 全局执行器实例
try:
    code_executor = DockerCodeExecutor()
except CodeExecutionError:
    logger.warning("Docker 不可用，代码执行功能将被禁用")
    code_executor = None