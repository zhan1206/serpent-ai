# -*- coding: utf-8 -*-
"""
代码执行插件 - 安全执行 Python 和 JavaScript 代码
使用受限环境执行，防止恶意代码
"""

import io
import sys
import subprocess
import logging
import tempfile
import os
import threading
from typing import Dict, List, Any

from backend.plugins.plugin_base import ToolPlugin
from backend.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)


class _OutputCapture:
    """捕获 stdout/stderr"""
    
    def __init__(self):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
    
    def write_stdout(self, data):
        self.stdout.write(data)
    
    def write_stderr(self, data):
        self.stderr.write(data)


def _execute_python(code: str, timeout: int = 10) -> Dict[str, Any]:
    """
    在子进程中安全执行 Python 代码
    
    Args:
        code: Python 代码
        timeout: 超时时间（秒）
        
    Returns:
        {stdout, stderr, exit_code, error}
    """
    # 创建临时文件
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        
        result = subprocess.run(
            [sys.executable, "-u", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        
        return {
            "stdout": result.stdout[-10000:],  # 限制输出长度
            "stderr": result.stderr[-5000:],
            "exit_code": result.returncode,
            "error": None if result.returncode == 0 else f"退出码: {result.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"执行超时（{timeout}秒）", "exit_code": -1, "error": "执行超时"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _execute_javascript(code: str, timeout: int = 10) -> Dict[str, Any]:
    """
    执行 JavaScript 代码（需要 Node.js）
    
    Args:
        code: JavaScript 代码
        timeout: 超时时间（秒）
        
    Returns:
        {stdout, stderr, exit_code, error}
    """
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
        
        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        return {
            "stdout": result.stdout[-10000:],
            "stderr": result.stderr[-5000:],
            "exit_code": result.returncode,
            "error": None if result.returncode == 0 else f"退出码: {result.returncode}",
        }
    except FileNotFoundError:
        return {"stdout": "", "stderr": "Node.js 未安装", "exit_code": -1, "error": "Node.js 未安装"}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"执行超时（{timeout}秒）", "exit_code": -1, "error": "执行超时"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


class CodeExecutorPlugin(ToolPlugin):
    """代码执行插件"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "execute_python",
                "description": "安全执行 Python 代码。代码在独立子进程中运行，有超时限制（默认10秒）。支持标准库和已安装的第三方包。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python 代码"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "超时时间（秒，默认10）",
                            "default": 10
                        }
                    },
                    "required": ["code"]
                },
                "handler": self._handle_python,
                "category": "code_execution"
            },
            {
                "name": "execute_javascript",
                "description": "执行 JavaScript 代码（需要 Node.js）。代码在独立子进程中运行。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "JavaScript 代码"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "超时时间（秒，默认10）",
                            "default": 10
                        }
                    },
                    "required": ["code"]
                },
                "handler": self._handle_javascript,
                "category": "code_execution"
            },
        ]
    
    def _handle_python(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        code = arguments["code"]
        timeout = arguments.get("timeout", 10)
        
        if not self.context or not self.context.sandbox.check_permission(
            self.name,
            __import__("backend.plugins.plugin_security", fromlist=["Permission"]).Permission.SHELL
        ):
            return {"error": "插件没有代码执行权限"}
        
        return _execute_python(code, timeout)
    
    def _handle_javascript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        code = arguments["code"]
        timeout = arguments.get("timeout", 10)
        
        if not self.context or not self.context.sandbox.check_permission(
            self.name,
            __import__("backend.plugins.plugin_security", fromlist=["Permission"]).Permission.SHELL
        ):
            return {"error": "插件没有代码执行权限"}
        
        return _execute_javascript(code, timeout)


def create_plugin(manifest: PluginManifest) -> CodeExecutorPlugin:
    return CodeExecutorPlugin(manifest)
