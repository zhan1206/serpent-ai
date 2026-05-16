"""
Tool Executor - 工具执行器
执行工具调用、处理错误、返回结果，支持沙箱隔离和权限控制
"""

from typing import Any, Dict, List, Optional
import asyncio
from typing import Dict, Any, Optional
from .tool_registry import ToolRegistry, get_global_registry

import logging

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
        检查工具执行权限
        
        Args:
            tool_name: 工具名称
            context: 执行上下文
            
        Returns:
            是否有权限
        """
        # TODO: 实现基于RBAC的权限控制
        # 目前简单返回True，后续需要实现完整的权限系统
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
        # TODO: 实现Docker沙箱
        # 1. 创建临时Docker容器
        # 2. 将工具代码和参数复制到容器
        # 3. 执行工具
        # 4. 获取结果
        # 5. 清理容器
        
        logger.warning("Docker sandbox not yet implemented, executing without sandbox")
        return self.execute(tool_name, arguments)
    
    def _execute_in_gvisor(self, tool_name: str, arguments: Dict) -> Any:
        """在gVisor沙箱中执行工具"""
        # TODO: 实现gVisor沙箱
        logger.warning("gVisor sandbox not yet implemented, executing without sandbox")
        return self.execute(tool_name, arguments)
    
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
