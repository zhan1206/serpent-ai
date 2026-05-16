"""
工具集成层测试
"""
import pytest
import asyncio


class TestToolRegistry:
    """工具注册表测试"""
    
    @pytest.mark.asyncio
    async def test_register_tool(self):
        """测试注册工具"""
        from tools.tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        
        # 注册工具
        tool_def = {
            "name": "test_tool",
            "description": "测试工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                },
                "required": ["input"]
            }
        }
        
        await registry.register("test_tool", tool_def)
        
        # 获取工具
        tool = await registry.get_tool("test_tool")
        assert tool is not None
        assert tool["name"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """测试列出工具"""
        from tools.tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        
        # 注册多个工具
        for i in range(3):
            await registry.register(f"tool_{i}", {
                "name": f"tool_{i}",
                "description": f"工具{i}"
            })
        
        # 列出工具
        tools = await registry.list_tools()
        assert len(tools) >= 3
    
    @pytest.mark.asyncio
    async def test_search_tools(self):
        """测试搜索工具"""
        from tools.tool_registry import ToolRegistry
        
        registry = ToolRegistry()
        
        # 注册工具
        await registry.register("web_search", {
            "name": "web_search",
            "description": "搜索网页"
        })
        await registry.register("calculator", {
            "name": "calculator",
            "description": "计算器"
        })
        
        # 搜索
        results = await registry.search("web")
        assert any("web" in t["name"] for t in results)


class TestToolExecutor:
    """工具执行器测试"""
    
    @pytest.mark.asyncio
    async def test_execute(self):
        """测试执行工具"""
        from tools.tool_executor import ToolExecutor
        
        executor = ToolExecutor()
        
        # 定义简单工具
        def add(a: int, b: int) -> int:
            return a + b
        
        # 注册并执行
        result = await executor.execute(add, {"a": 1, "b": 2})
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """测试执行错误处理"""
        from tools.tool_executor import ToolExecutor
        
        executor = ToolExecutor()
        
        # 定义会出错的方法
        def divide(a: int, b: int) -> float:
            if b == 0:
                raise ValueError("不能除以0")
            return a / b
        
        # 执行应该失败
        result = await executor.execute(divide, {"a": 1, "b": 0})
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_batch_execute(self):
        """测试批量执行"""
        from tools.tool_executor import ToolExecutor
        
        executor = ToolExecutor()
        
        def add(a: int, b: int) -> int:
            return a + b
        
        # 批量执行
        tasks = [
            (add, {"a": 1, "b": 2}),
            (add, {"a": 3, "b": 4}),
            (add, {"a": 5, "b": 6}),
        ]
        
        results = await executor.batch_execute(tasks)
        assert len(results) == 3
        assert results[0] == 3


class TestToolPrecompiler:
    """工具预编译器测试"""
    
    @pytest.mark.asyncio
    async def test_compile(self):
        """测试编译工具描述"""
        from tools.tool_precompiler import ToolPrecompiler
        
        precompiler = ToolPrecompiler()
        
        # 原始工具描述
        tool_desc = {
            "name": "calculator",
            "description": "A calculator tool that performs basic arithmetic operations. It supports addition, subtraction, multiplication, and division. Input should be a valid mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate, e.g., '2 + 2' or '10 * 5'"
                    }
                },
                "required": ["expression"]
            }
        }
        
        # 编译
        compiled = await precompiler.compile(tool_desc)
        assert compiled is not None
        assert compiled["id"] is not None
    
    @pytest.mark.asyncio
    async def test_generate_id(self):
        """测试ID生成"""
        from tools.tool_precompiler import ToolPrecompiler
        
        precompiler = ToolPrecompiler()
        
        # 生成ID
        id1 = await precompiler.generate_id("test_tool")
        id2 = await precompiler.generate_id("test_tool")
        
        # 相同工具应该生成相同ID
        assert id1 == id2


class TestToolDistiller:
    """工具蒸馏器测试"""
    
    @pytest.mark.asyncio
    async def test_distill(self):
        """测试蒸馏工具描述"""
        from tools.tool_distiller import ToolDistiller
        
        distiller = ToolDistiller()
        
        # 原始详细描述
        original = {
            "name": "web_search",
            "description": "This is a powerful web search tool that allows you to search the internet for information. It can search for any topic you specify and return relevant results. You can specify the number of results you want and the search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string that you want to search for on the web"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "The maximum number of search results to return, default is 10"
                    }
                },
                "required": ["query"]
            }
        }
        
        # 蒸馏
        distilled = await distiller.distill(original)
        assert distilled is not None
        # 蒸馏后应该更短
        assert len(distilled["description"]) <= len(original["description"])


class TestBuiltinTools:
    """内置工具测试"""
    
    @pytest.mark.asyncio
    async def test_list_builtin_tools(self):
        """测试列出内置工具"""
        from tools.builtin_tools import list_builtin_tools
        
        tools = await list_builtin_tools()
        assert isinstance(tools, list)
    
    @pytest.mark.asyncio
    async def test_search_builtin_tools(self):
        """测试搜索内置工具"""
        from tools.builtin_tools import search_builtin_tools
        
        results = await search_builtin_tools("search")
        assert isinstance(results, list)