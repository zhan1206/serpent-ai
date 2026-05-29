"""
工具集成层测试
"""
import pytest


class TestToolRegistry:
    """工具注册表测试"""

    def test_register_builtin_tool(self):
        """测试注册内置工具"""
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        tool_def = {
            "name": "test_tool",
            "description": "测试工具",
            "parameters": {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"]
            }
        }
        registry.register_builtin_tool(tool_def)
        tool = registry.get_tool("test_tool")
        assert tool is not None
        assert tool["name"] == "test_tool"

    def test_register_custom_tool(self):
        """测试注册自定义工具"""
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        registry.register_custom_tool({"name": "custom_tool", "description": "自定义", "parameters": {}})
        assert registry.get_tool("custom_tool") is not None

    def test_list_tools(self):
        from backend.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        for i in range(3):
            registry.register_builtin_tool({"name": f"tool_{i}", "description": f"工具{i}"})
        tools = registry.list_tools()
        assert len(tools) >= 3

    def test_search_tools(self):
        from backend.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "web_search", "description": "搜索网页"})
        registry.register_builtin_tool({"name": "calculator", "description": "计算器"})
        results = registry.search_tools("web")
        assert len(results) > 0

    def test_remove_tool(self):
        from backend.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "temp_tool", "description": "临时"})
        assert registry.get_tool("temp_tool") is not None
        registry.remove_tool("temp_tool")
        assert registry.get_tool("temp_tool") is None

    def test_clear(self):
        from backend.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "t1", "description": "d1"})
        registry.clear()
        assert len(registry.list_tools()) == 0

    def test_list_categories(self):
        from backend.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        categories = registry.list_categories()
        assert isinstance(categories, (list, set, tuple, dict))


class TestToolExecutor:
    """工具执行器测试"""

    def test_create_executor(self):
        from backend.tools.tool_executor import ToolExecutor
        executor = ToolExecutor()
        assert executor is not None
        assert executor.registry is not None

    def test_executor_methods(self):
        from backend.tools.tool_executor import ToolExecutor
        executor = ToolExecutor()
        assert hasattr(executor, 'execute')
        assert hasattr(executor, 'batch_execute')
        assert hasattr(executor, 'execute_in_sandbox')

    def test_executor_config(self):
        from backend.tools.tool_executor import ToolExecutor
        executor = ToolExecutor()
        assert executor.timeout is not None
        assert executor.max_retries is not None


class TestToolPrecompiler:
    """工具预编译器测试"""

    def test_precompile_tool(self):
        from backend.tools.tool_precompiler import ToolPrecompiler
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "calculator", "description": "计算器", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}})

        precompiler = ToolPrecompiler(registry)
        compiled = precompiler.precompile_tool("calculator")
        assert compiled is not None

    def test_get_tool_id(self):
        from backend.tools.tool_precompiler import ToolPrecompiler
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "test_tool", "description": "测试"})

        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_tool("test_tool")
        tool_id = precompiler.get_tool_id("test_tool")
        assert tool_id is not None
        assert precompiler.get_tool_name(tool_id) == "test_tool"

    def test_precompile_all(self):
        from backend.tools.tool_precompiler import ToolPrecompiler
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        for i in range(3):
            registry.register_builtin_tool({"name": f"tool_{i}", "description": f"工具{i}"})

        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_all()
        assert len(precompiler.compiled_tools) >= 3

    def test_get_tools_prompt(self):
        from backend.tools.tool_precompiler import ToolPrecompiler
        from backend.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "calc", "description": "计算器"})
        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_tool("calc")
        prompt = precompiler.get_tools_prompt()
        assert isinstance(prompt, str)


class TestToolDistiller:
    """工具蒸馏器测试"""

    def test_distill_tool(self):
        from backend.tools.tool_distiller import ToolDistiller
        from backend.tools.tool_registry import ToolRegistry
        from backend.tools.tool_precompiler import ToolPrecompiler

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "web_search", "description": "A powerful web search tool."})
        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_tool("web_search")

        distiller = ToolDistiller(registry, precompiler)
        distilled = distiller.distill_tool("web_search")
        assert distilled is not None

    def test_distill_all(self):
        from backend.tools.tool_distiller import ToolDistiller
        from backend.tools.tool_registry import ToolRegistry
        from backend.tools.tool_precompiler import ToolPrecompiler

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "t1", "description": "工具1"})
        registry.register_builtin_tool({"name": "t2", "description": "工具2"})
        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_all()

        distiller = ToolDistiller(registry, precompiler)
        distiller.distill_all()
        assert len(distiller.distilled_tools) >= 2

    def test_get_distilled_prompt(self):
        from backend.tools.tool_distiller import ToolDistiller
        from backend.tools.tool_registry import ToolRegistry
        from backend.tools.tool_precompiler import ToolPrecompiler

        registry = ToolRegistry()
        registry.register_builtin_tool({"name": "calc", "description": "计算器"})
        precompiler = ToolPrecompiler(registry)
        precompiler.precompile_tool("calc")

        distiller = ToolDistiller(registry, precompiler)
        distiller.distill_tool("calc")
        prompt = distiller.get_distilled_prompt()
        assert isinstance(prompt, str)


class TestBuiltinTools:
    """内置工具测试"""

    def test_list_builtin_tools(self):
        from backend.tools.builtin_tools import list_builtin_tools
        tools = list_builtin_tools()
        assert isinstance(tools, list)

    def test_search_builtin_tools(self):
        from backend.tools.builtin_tools import search_builtin_tools
        results = search_builtin_tools("search")
        assert isinstance(results, list)
