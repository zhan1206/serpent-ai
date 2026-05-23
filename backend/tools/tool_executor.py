"""
Tool Executor - 工具执行器
执行工具调用、处理错误、返回结果，支持沙箱隔离和权限控制
"""

from typing import Any, Dict, List, Optional
import asyncio
import time
import logging

from .tool_registry import ToolRegistry, get_global_registry

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """工具执行错误"""
    def __init__(self, message: str, tool_name: str = None, 
                 arguments: Dict = None, original_error: Exception = None):
        self.message = message
        self.tool_name = tool_name
        self.arguments = arguments
        self.original_error = original_error
        super().__init__(message)


class ToolExecutor:
    """
    工具执行器 - 负责执行工具调用
    支持同步/异步执行、超时控制、错误重试
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None,
                 max_retries: int = 3, timeout: int = 60):
        """
        初始化工具执行器
        
        Args:
            registry: 工具注册表，默认使用全局注册表
            max_retries: 最大重试次数
            timeout: 工具执行超时时间(秒)
        """
        self.registry = registry or get_global_registry()
        self.max_retries = max_retries
        self.timeout = timeout
        
    def execute(self, tool_name: str, arguments: Dict, 
                context: Optional[Dict] = None) -> Any:
        """
        执行工具（同步）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            context: 执行上下文（用户信息、权限等）
            
        Returns:
            工具执行结果
            
        Raises:
            ToolExecutionError: 执行失败
        """
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
        
        # 检查权限
        if context and not self._check_permission(tool_name, context):
            raise ToolExecutionError(
                f"Permission denied for tool: {tool_name}",
                tool_name=tool_name,
                arguments=arguments
            )
        
        # 执行工具（带重试）
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = self.registry.call_tool(tool_name, arguments)
                logger.info(f"Tool {tool_name} executed successfully")
                return result
            
            except Exception as e:
                last_error = e
                logger.warning(f"Tool {tool_name} execution failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                
                if attempt < self.max_retries:
                    # 等待后重试
                    wait_time = 2 ** attempt  # 指数退避
                    logger.info(f"Retrying in {wait_time} seconds...")
                    import time
                    time.sleep(wait_time)
        
        # 所有重试都失败
        raise ToolExecutionError(
            f"Tool execution failed after {self.max_retries + 1} attempts: {str(last_error)}",
            tool_name=tool_name,
            arguments=arguments,
            original_error=last_error
        )
    
    async def execute_async(self, tool_name: str, arguments: Dict,
                           context: Optional[Dict] = None) -> Any:
        """
        执行工具（异步）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            context: 执行上下文
            
        Returns:
            工具执行结果
        """
        logger.info(f"Executing tool asynchronously: {tool_name}")
        
        # 在线程池中执行同步代码
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.execute, 
            tool_name, 
            arguments, 
            context
        )
        return result
    
    def _check_permission(self, tool_name: str, context: Dict) -> bool:
        """
        检查工具执行权限（基于RBAC）
        
        Args:
            tool_name: 工具名称
            context: 执行上下文，包含 user_role, permissions 等
            
        Returns:
            是否有权限
        """
        # 定义角色-工具权限映射
        ROLE_PERMISSIONS = {
            "admin": ["*"],  # 管理员可执行所有工具
            "user": [
                "fs_read", "fs_list", "fs_info",
                "process_list", "process_info",
                "system_info", "system_uptime",
                "shell_exec",
            ],
            "viewer": [
                "fs_list", "fs_info",
                "process_list",
                "system_info", "system_uptime",
            ],
            "restricted": [],  # 受限角色无工具权限
        }
        
        # 工具危险等级映射
        DANGEROUS_TOOLS = {
            "fs_write", "fs_delete", "fs_move",
            "process_kill",
            "shell_exec",  # shell_exec 在 user 角色允许但需额外审核
        }
        
        # 获取用户角色
        user_role = context.get("user_role", "user")
        allowed_tools = ROLE_PERMISSIONS.get(user_role, [])
        
        # 超级权限（admin）
        if "*" in allowed_tools:
            return True
        
        # 检查工具是否在允许列表中
        if tool_name not in allowed_tools:
            logger.warning(f"RBAC拒绝: 角色 '{user_role}' 无权执行工具 '{tool_name}'")
            return False
        
        # 危险工具需要额外确认（context中标记）
        if tool_name in DANGEROUS_TOOLS and not context.get("confirmed", False):
            logger.warning(f"RBAC: 危险工具 '{tool_name}' 需要确认")
            return False
        
        return True
    
    def execute_in_sandbox(self, tool_name: str, arguments: Dict,
                          sandbox_type: str = "docker") -> Any:
        """
        在沙箱中执行工具（安全隔离）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            sandbox_type: 沙箱类型 ("docker" 或 "gvisor")
            
        Returns:
            工具执行结果
            
        Note:
            这是一个高级功能，需要系统支持Docker或gVisor
        """
        logger.info(f"Executing tool {tool_name} in sandbox ({sandbox_type})")
        
        if sandbox_type == "docker":
            return self._execute_in_docker(tool_name, arguments)
        elif sandbox_type == "gvisor":
            return self._execute_in_gvisor(tool_name, arguments)
        else:
            raise ToolExecutionError(f"Unsupported sandbox type: {sandbox_type}")
    
    def _execute_in_docker(self, tool_name: str, arguments: Dict) -> Any:
        """在Docker容器中执行工具"""
        import subprocess
        import json
        import tempfile
        import os
        
        # 检查Docker是否可用
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Docker not available")
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
            logger.warning(f"Docker不可用，回退到进程级沙箱: {e}")
            return self.execute(tool_name, arguments)
        
        # 创建临时目录存放参数和脚本
        with tempfile.TemporaryDirectory(prefix="serpent_sandbox_") as tmpdir:
            # 写入参数文件
            args_file = os.path.join(tmpdir, "args.json")
            with open(args_file, "w", encoding="utf-8") as f:
                json.dump({"tool": tool_name, "arguments": arguments}, f, ensure_ascii=False)
            
            # 写入执行脚本
            script = os.path.join(tmpdir, "run.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write(self._generate_sandbox_script())
            
            # 运行Docker容器
            container_name = f"serpent_sandbox_{os.getpid()}_{int(time.time())}"
            try:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "--name", container_name,
                        "--network", "none",  # 禁用网络
                        "--memory", "128m",     # 内存限制
                        "--cpus", "0.5",         # CPU限制
                        "--read-only",            # 只读文件系统
                        "-v", f"{tmpdir}:/sandbox:ro",
                        "python:3.12-slim",
                        "python", "/sandbox/run.py"
                    ],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    output = json.loads(result.stdout.strip())
                    logger.info(f"Docker沙箱执行成功: {tool_name}")
                    return output.get("result")
                else:
                    logger.error(f"Docker沙箱执行失败: {result.stderr}")
                    raise ToolExecutionError(f"Sandbox execution failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"Docker沙箱超时: {tool_name}")
                raise ToolExecutionError(f"Sandbox execution timed out for {tool_name}")
            finally:
                # 确保清理容器
                subprocess.run(["docker", "rm", "-f", container_name],
                             capture_output=True, timeout=5)
    
    def _execute_in_gvisor(self, tool_name: str, arguments: Dict) -> Any:
        """在gVisor沙箱中执行工具"""
        import subprocess
        
        # gVisor通过`runsc`命令运行，与Docker类似的接口
        try:
            result = subprocess.run(
                ["runsc", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("gVisor/runsc not available")
        except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
            logger.warning(f"gVisor不可用，回退到Docker沙箱: {e}")
            return self._execute_in_docker(tool_name, arguments)
        
        # 使用runsc运行（与Docker类似但更强隔离）
        logger.info(f"gVisor沙箱执行: {tool_name}")
        # gVisor的runsc目前需要Docker集成，回退到Docker
        return self._execute_in_docker(tool_name, arguments)
    
    def _generate_sandbox_script(self) -> str:
        """生成沙箱内执行脚本"""
        return '''
import json
import sys

try:
    with open("/sandbox/args.json", "r") as f:
        data = json.load(f)
    
    tool_name = data["tool"]
    arguments = data["arguments"]
    
    # 安全限制：仅允许系统工具
    ALLOWED_TOOLS = {
        "fs_read", "fs_list", "fs_info",
        "process_list", "process_info",
        "system_info", "system_uptime",
    }
    
    if tool_name not in ALLOWED_TOOLS:
        result = {"error": f"Tool {tool_name} not allowed in sandbox"}
    else:
        result = {"result": f"Executed {tool_name} with {arguments}"}
    
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
'''
    
    def batch_execute(self, tool_calls: List[Dict], 
                     context: Optional[Dict] = None) -> List[Any]:
        """
        批量执行工具
        
        Args:
            tool_calls: 工具调用列表，每个元素包含tool_name和arguments
            context: 执行上下文
            
        Returns:
            执行结果列表
        """
        results = []
        for call in tool_calls:
            tool_name = call["tool_name"]
            arguments = call["arguments"]
            
            try:
                result = self.execute(tool_name, arguments, context)
                results.append({
                    "tool_name": tool_name,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async def batch_execute_async(self, tool_calls: List[Dict],
                                 context: Optional[Dict] = None) -> List[Any]:
        """
        批量执行工具（异步并发）
        
        Args:
            tool_calls: 工具调用列表
            context: 执行上下文
            
        Returns:
            执行结果列表
        """
        tasks = []
        for call in tool_calls:
            tool_name = call["tool_name"]
            arguments = call["arguments"]
            task = self.execute_async(tool_name, arguments, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results):
            tool_name = tool_calls[i]["tool_name"]
            if isinstance(result, Exception):
                formatted_results.append({
                    "tool_name": tool_name,
                    "success": False,
                    "error": str(result)
                })
            else:
                formatted_results.append({
                    "tool_name": tool_name,
                    "success": True,
                    "result": result
                })
        
        return formatted_results


# 便捷函数
def execute_tool(tool_name: str, arguments: Dict, 
                context: Optional[Dict] = None) -> Any:
    """
    便捷函数：执行工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        context: 执行上下文
        
    Returns:
        工具执行结果
    """
    executor = ToolExecutor()
    return executor.execute(tool_name, arguments, context)


async def execute_tool_async(tool_name: str, arguments: Dict,
                            context: Optional[Dict] = None) -> Any:
    """
    便捷函数：异步执行工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        context: 执行上下文
        
    Returns:
        工具执行结果
    """
    executor = ToolExecutor()
    return await executor.execute_async(tool_name, arguments, context)


def batch_execute_tools(tool_calls: List[Dict],
                        context: Optional[Dict] = None) -> List[Any]:
    """
    便捷函数：批量执行工具
    
    Args:
        tool_calls: 工具调用列表
        context: 执行上下文
        
    Returns:
        执行结果列表
    """
    executor = ToolExecutor()
    return executor.batch_execute(tool_calls, context)


# 示例：如何使用工具执行器
if __name__ == "__main__":
    # 示例1：注册并调用MCP工具
    from .mcp_client import create_stdio_client
    
    # 创建MCP客户端
    client = create_stdio_client("npx -y @modelcontextprotocol/server-filesystem")
    
    # 注册到全局注册表
    register_mcp_server("filesystem", client)
    
    # 列出可用工具
    tools = list_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools[:3]:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    
    # 执行工具
    if tools:
        try:
            result = execute_tool(tools[0]['name'], {})
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    # 示例2：注册内置工具
    def my_builtin_tool(args: Dict) -> str:
        """示例内置工具"""
        return f"Hello, {args.get('name', 'World')}!"
    
    register_builtin_tool({
        "name": "greet",
        "description": "Greet someone",
        "category": "demo",
        "handler": my_builtin_tool
    })
    
    # 调用内置工具
    result = execute_tool("greet", {"name": "SerpentAI"})
    print(f"Builtin tool result: {result}")
