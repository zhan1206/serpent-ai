"""
SerpentAI Tool Integration Layer
工具集成层 - 实现MCP协议，支持1000+工具
"""

from .mcp_client import MCPClient, MCPError

__all__ = ['MCPClient', 'MCPError']
