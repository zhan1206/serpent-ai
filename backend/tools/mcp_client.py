"""
MCP (Model Context Protocol) Client Implementation
完整实现MCP协议，支持stdio和HTTP传输
"""

import json
import subprocess
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP协议错误"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


class MCPClient:
    """
    MCP协议客户端
    支持stdio和HTTP传输，实现JSON-RPC 2.0
    """
    
    def __init__(self, transport: str = "stdio", command: Optional[str] = None, 
                 url: Optional[str] = None, timeout: int = 30):
        """
        初始化MCP客户端
        
        Args:
            transport: 传输方式 ("stdio" 或 "http")
            command: stdio模式下的命令 (例如: "npx -y @modelcontextprotocol/server-filesystem")
            url: HTTP模式下的URL
            timeout: 超时时间(秒)
        """
        self.transport = transport
        self.command = command
        self.url = url
        self.timeout = timeout
        
        self.process = None
        self.request_id = 0
        self.lock = threading.Lock()
        
        # 缓存已列出的工具
        self._tools_cache = None
        
    def _next_id(self) -> int:
        """生成下一个请求ID"""
        with self.lock:
            self.request_id += 1
            return self.request_id
    
    def _send_stdio_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        通过stdio发送JSON-RPC 2.0请求
        
        Args:
            method: RPC方法名
            params: 方法参数
            
        Returns:
            响应结果
        """
        if not self.process:
            if not self.command:
                raise MCPError(-1, "No command provided for stdio transport")
            
            # 启动MCP服务器进程
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # 行缓冲
            )
        
        # 构造JSON-RPC 2.0请求
        request_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # 发送请求
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        # 读取响应
        response_str = self.process.stdout.readline()
        if not response_str:
            raise MCPError(-1, "No response from MCP server")
        
        response = json.loads(response_str)
        
        # 检查是否是对应请求的响应
        if response.get("id") != request_id:
            raise MCPError(-1, "Response ID mismatch")
        
        # 检查是否有错误
        if "error" in response:
            error = response["error"]
            raise MCPError(error["code"], error["message"], error.get("data"))
        
        return response.get("result")
    
    def _send_http_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        通过HTTP发送JSON-RPC 2.0请求
        
        Args:
            method: RPC方法名
            params: 方法参数
            
        Returns:
            响应结果
        """
        if not self.url:
            raise MCPError(-1, "No URL provided for HTTP transport")
        
        try:
            import requests
        except ImportError:
            raise MCPError(-1, "requests library not installed. Install with: pip install requests")
        
        # 构造JSON-RPC 2.0请求
        request_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # 发送HTTP请求
        response = requests.post(
            self.url,
            json=request,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        
        # 检查是否有错误
        if "error" in result:
            error = result["error"]
            raise MCPError(error["code"], error["message"], error.get("data"))
        
        return result.get("result")
    
    def connect(self) -> Dict:
        """
        连接到MCP服务器并初始化
        
        Returns:
            服务器能力信息
        """
        if self.transport == "stdio":
            return self._send_stdio_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "SerpentAI",
                    "version": "1.0.0"
                }
            })
        elif self.transport == "http":
            return self._send_http_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "SerpentAI",
                    "version": "1.0.0"
                }
            })
        else:
            raise MCPError(-1, f"Unsupported transport: {self.transport}")
    
    def list_tools(self, force_refresh: bool = False) -> List[Dict]:
        """
        列出MCP服务器提供的所有工具
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            工具列表，每个工具包含name, description, inputSchema
        """
        if self._tools_cache is not None and not force_refresh:
            return self._tools_cache
        
        if self.transport == "stdio":
            result = self._send_stdio_request("tools/list")
        elif self.transport == "http":
            result = self._send_http_request("tools/list")
        else:
            raise MCPError(-1, f"Unsupported transport: {self.transport}")
        
        self._tools_cache = result.get("tools", [])
        return self._tools_cache
    
    def call_tool(self, name: str, arguments: Dict) -> Any:
        """
        调用MCP工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if self.transport == "stdio":
            result = self._send_stdio_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
        elif self.transport == "http":
            result = self._send_http_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
        else:
            raise MCPError(-1, f"Unsupported transport: {self.transport}")
        
        return result
    
    def close(self):
        """关闭MCP客户端连接"""
        if self.process:
            self.process.terminate()
            self.process = None
        self._tools_cache = None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# 便捷函数
def create_stdio_client(command: str, timeout: int = 30) -> MCPClient:
    """
    创建stdio传输的MCP客户端
    
    Args:
        command: MCP服务器启动命令
        timeout: 超时时间(秒)
        
    Returns:
        MCPClient实例
    """
    return MCPClient(transport="stdio", command=command, timeout=timeout)


def create_http_client(url: str, timeout: int = 30) -> MCPClient:
    """
    创建HTTP传输的MCP客户端
    
    Args:
        url: MCP服务器URL
        timeout: 超时时间(秒)
        
    Returns:
        MCPClient实例
    """
    return MCPClient(transport="http", url=url, timeout=timeout)


# 示例：如何使用MCP客户端
if __name__ == "__main__":
    # 示例1: 使用stdio传输连接到文件系统MCP服务器
    try:
        with create_stdio_client("npx -y @modelcontextprotocol/server-filesystem") as client:
            # 列出工具
            tools = client.list_tools()
            print(f"Available tools: {len(tools)}")
            for tool in tools[:3]:  # 只显示前3个
                print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
            
            # 调用工具
            if tools:
                result = client.call_tool(tools[0]['name'], {})
                print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 示例2: 使用HTTP传输
    # with create_http_client("http://localhost:8080/mcp") as client:
    #     tools = client.list_tools()
    #     print(f"Available tools: {len(tools)}")
