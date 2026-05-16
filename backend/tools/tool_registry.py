"""
Tool Registry - 工具注册表
管理1000+工具的元数据、缓存、搜索和过滤
"""

import json
import logging
from typing import Dict, List, Optional, Any
from .mcp_client import MCPClient, MCPError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表 - 管理所有可用工具
    支持MCP工具、内置工具和自定义工具
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self.tools: Dict[str, Dict] = {}  # tool_name -> tool_metadata
        self.mcp_clients: Dict[str, MCPClient] = {}  # server_name -> MCPClient
        self.categories: Dict[str, List[str]] = {}  # category -> [tool_names]
        
    def register_mcp_server(self, server_name: str, client: MCPClient, 
                           auto_connect: bool = True) -> List[Dict]:
        """
        注册MCP服务器，自动获取该服务器提供的所有工具
        
        Args:
            server_name: 服务器名称（用于标识）
            client: MCP客户端实例
            auto_connect: 是否自动连接
            
        Returns:
            注册的工具列表
        """
        if auto_connect:
            client.connect()
        
        # 获取工具列表
        tools = client.list_tools()
        
        # 注册每个工具
        registered = []
        for tool in tools:
            tool_name = tool["name"]
            # 添加服务器信息到工具元数据
            tool["server"] = server_name
            tool["type"] = "mcp"
            
            # 生成唯一工具ID（如果重名，添加服务器前缀）
            unique_name = f"{server_name}.{tool_name}" if tool_name in self.tools else tool_name
            tool["unique_name"] = unique_name
            
            self.tools[unique_name] = tool
            registered.append(tool)
            
            # 更新分类
            category = tool.get("category", "uncategorized")
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(unique_name)
        
        # 保存MCP客户端引用
        self.mcp_clients[server_name] = client
        
        logger.info(f"Registered MCP server '{server_name}' with {len(registered)} tools")
        return registered
    
    def register_builtin_tool(self, tool: Dict):
        """
        注册内置工具
        
        Args:
            tool: 工具元数据，包含name, description, inputSchema, handler等
        """
        tool_name = tool["name"]
        tool["type"] = "builtin"
        tool["server"] = "serpentai"
        tool["unique_name"] = tool_name
        
        self.tools[tool_name] = tool
        
        # 更新分类
        category = tool.get("category", "uncategorized")
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(tool_name)
        
        logger.info(f"Registered builtin tool: {tool_name}")
    
    def register_custom_tool(self, tool: Dict):
        """
        注册自定义工具
        
        Args:
            tool: 工具元数据
        """
        tool_name = tool["name"]
        tool["type"] = "custom"
        tool["server"] = "user"
        tool["unique_name"] = tool_name
        
        self.tools[tool_name] = tool
        
        # 更新分类
        category = tool.get("category", "uncategorized")
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(tool_name)
        
        logger.info(f"Registered custom tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Dict]:
        """
        获取工具元数据
        
        Args:
            tool_name: 工具名称（可以是原始名称或唯一名称）
            
        Returns:
            工具元数据，如果不存在返回None
        """
        # 先尝试直接查找
        if tool_name in self.tools:
            return self.tools[tool_name]
        
        # 尝试查找唯一名称（server.tool_name格式）
        for name, tool in self.tools.items():
            if tool["name"] == tool_name:
                return tool
        
        return None
    
    def list_tools(self, category: Optional[str] = None, 
                  tool_type: Optional[str] = None) -> List[Dict]:
        """
        列出所有工具
        
        Args:
            category: 按分类过滤
            tool_type: 按类型过滤 (mcp/builtin/custom)
            
        Returns:
            工具列表
        """
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.get("category") == category]
        
        if tool_type:
            tools = [t for t in tools if t.get("type") == tool_type]
        
        return tools
    
    def search_tools(self, query: str) -> List[Dict]:
        """
        搜索工具（按名称、描述）
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的工具列表
        """
        query = query.lower()
        results = []
        
        for tool in self.tools.values():
            name = tool.get("name", "").lower()
            description = tool.get("description", "").lower()
            
            if query in name or query in description:
                results.append(tool)
        
        return results
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool_type = tool.get("type")
        
        if tool_type == "mcp":
            # 调用MCP工具
            server_name = tool["server"]
            client = self.mcp_clients.get(server_name)
            if not client:
                raise ValueError(f"MCP client not found for server: {server_name}")
            
            # 使用原始工具名称（不包含服务器前缀）
            original_name = tool["name"]
            return client.call_tool(original_name, arguments)
        
        elif tool_type == "builtin":
            # 调用内置工具
            handler = tool.get("handler")
            if not handler:
                raise ValueError(f"No handler for builtin tool: {tool_name}")
            return handler(arguments)
        
        elif tool_type == "custom":
            # 调用自定义工具
            handler = tool.get("handler")
            if not handler:
                raise ValueError(f"No handler for custom tool: {tool_name}")
            return handler(arguments)
        
        else:
            raise ValueError(f"Unknown tool type: {tool_type}")
    
    def list_categories(self) -> Dict[str, int]:
        """
        列出所有工具分类及其工具数量
        
        Returns:
            {分类名: 工具数量}
        """
        return {cat: len(tools) for cat, tools in self.categories.items()}
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        移除工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否成功移除
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        unique_name = tool["unique_name"]
        
        # 从tools中移除
        if unique_name in self.tools:
            del self.tools[unique_name]
        
        # 从分类中移除
        category = tool.get("category", "uncategorized")
        if category in self.categories and unique_name in self.categories[category]:
            self.categories[category].remove(unique_name)
        
        logger.info(f"Removed tool: {unique_name}")
        return True
    
    def clear(self):
        """清空所有工具"""
        self.tools.clear()
        self.mcp_clients.clear()
        self.categories.clear()
        logger.info("Cleared all tools")


# 全局工具注册表实例
_global_registry = None


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册表实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_mcp_server(server_name: str, client: MCPClient, 
                       auto_connect: bool = True) -> List[Dict]:
    """注册MCP服务器到全局注册表"""
    registry = get_global_registry()
    return registry.register_mcp_server(server_name, client, auto_connect)


def register_builtin_tool(tool: Dict):
    """注册内置工具到全局注册表"""
    registry = get_global_registry()
    registry.register_builtin_tool(tool)


def register_custom_tool(tool: Dict):
    """注册自定义工具到全局注册表"""
    registry = get_global_registry()
    registry.register_custom_tool(tool)


def get_tool(tool_name: str) -> Optional[Dict]:
    """从全局注册表获取工具"""
    registry = get_global_registry()
    return registry.get_tool(tool_name)


def list_tools(category: Optional[str] = None, 
              tool_type: Optional[str] = None) -> List[Dict]:
    """从全局注册表列出工具"""
    registry = get_global_registry()
    return registry.list_tools(category, tool_type)


def call_tool(tool_name: str, arguments: Dict) -> Any:
    """通过全局注册表调用工具"""
    registry = get_global_registry()
    return registry.call_tool(tool_name, arguments)
