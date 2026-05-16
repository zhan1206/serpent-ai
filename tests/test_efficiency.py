"""
效率引擎层测试
"""
import pytest
import asyncio


class TestTokenOptimizer:
    """Token优化器测试"""
    
    @pytest.mark.asyncio
    async def test_calculate_tokens(self):
        """测试Token计算"""
        from efficiency import TokenOptimizer
        
        calc = TokenOptimizer()
        
        # 测试文本Token计算
        text = "你好，这是一段测试文本"
        tokens = await calc.calculate(text)
        assert tokens > 0
    
    @pytest.mark.asyncio
    async def test_optimize_prompt(self):
        """测试提示词优化"""
        from efficiency import PromptOptimizer
        
        optimizer = PromptOptimizer()
        
        # 原始提示词
        prompt = {
            "system": "你是一个有用的AI助手。你应该提供准确、有帮助的回答。"
        }
        
        # 优化
        optimized = await optimizer.optimize(prompt)
        assert optimized is not None
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试统计信息"""
        from efficiency import get_global_engine
        
        optimizer = get_global_engine()
        stats = optimizer.get_stats()
        
        assert isinstance(stats, dict)


class TestPromptDistiller:
    """提示词蒸馏器测试"""
    
    @pytest.mark.asyncio
    async def test_distill_system_prompt(self):
        """测试系统提示词蒸馏"""
        from efficiency import PromptDistiller
        
        distiller = PromptDistiller()
        
        # 原始详细提示词
        original = """你是一个专业的AI助手。
        
你是用Python、JavaScript、Go等多种编程语言专家。
你有10年的软件开发经验。
你可以帮助用户解决各种编程问题。
你擅长Web开发、移动端开发、后端开发。
你了解最新的AI技术和工具。
你能够提供高质量的代码示例和解释。
你总是在回答中保持友好和专业。"""
        
        # 蒸馏
        distilled = await distiller.distill(original)
        
        # 蒸馏后应该更短
        assert len(distilled) < len(original)
    
    @pytest.mark.asyncio
    async def test_cache(self):
        """测试缓存"""
        from efficiency import PromptDistiller
        
        distiller = PromptDistiller()
        
        # 第一次蒸馏
        result1 = await distiller.distill("测试1")
        
        # 第二次相同内容应该从缓存获取
        result2 = await distiller.distill("测试1")
        
        assert result1 == result2


class TestIncrementalContextManager:
    """增量上下文管理器测试"""
    
    @pytest.mark.asyncio
    async def test_get_incremental(self):
        """测试增量获取"""
        from efficiency import IncrementalContextManager
        
        manager = IncrementalContextManager()
        
        # 完整消息历史
        messages = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "消息1"},
            {"role": "assistant", "content": "回复1"},
            {"role": "user", "content": "消息2"},
            {"role": "assistant", "content": "回复2"},
            {"role": "user", "content": "消息3"},
        ]
        
        # 获取增量
        incremental = await manager.get_incremental(messages, last_state=None)
        
        # 应该返回完整消息（因为第一次没有状态）
        assert len(incremental) > 0
    
    @pytest.mark.asyncio
    async def test_save_state(self):
        """测试状态保存"""
        from efficiency import IncrementalContextManager
        
        manager = IncrementalContextManager()
        
        # 消息列表
        messages = [
            {"role": "user", "content": "测试"},
        ]
        
        # 保存状态
        state = await manager.save_state(messages)
        
        assert state is not None
    
    @pytest.mark.asyncio
    async def test_restore_state(self):
        """测试状态恢复"""
        from efficiency import IncrementalContextManager
        
        manager = IncrementalContextManager()
        
        # 保存状态
        messages = [
            {"role": "user", "content": "测试"},
        ]
        state = await manager.save_state(messages)
        
        # 恢复状态
        restored = await manager.restore_state(state)
        
        assert len(restored) > 0


class TestSemanticCompressor:
    """语义压缩器测试"""
    
    @pytest.mark.asyncio
    async def test_compress(self):
        """测试压缩"""
        from efficiency import SemanticCompressor
        
        compressor = SemanticCompressor()
        
        # 对话历史
        history = [
            {"role": "user", "content": "我想学习Python编程"},
            {"role": "assistant", "content": "Python是一种高级编程语言，语法简洁优雅..."},
            {"role": "user", "content": "怎么安装"},
            {"role": "assistant", "content": "可以使用pip install python来安装..."},
            {"role": "user", "content": "谢谢"},
            {"role": "assistant", "content": "不客气！"},
        ]
        
        # 压缩
        compressed = await compressor.compress(history, target_ratio=0.5)
        
        # 应该更短
        assert len(compressed) <= len(history)
        # 应该保留关键信息
        assert any("Python" in str(m) for m in compressed)
    
    @pytest.mark.asyncio
    async def test_extract_key_points(self):
        """测试关键点提取"""
        from efficiency import SemanticCompressor
        
        compressor = SemanticCompressor()
        
        # 对话
        history = [
            {"role": "user", "content": "我喜欢蓝色"},
            {"role": "assistant", "content": "蓝色是很美的颜色"},
        ]
        
        # 提取
        key_points = await compressor.extract_key_points(history)
        
        assert isinstance(key_points, list)


class TestMultiLevelCache:
    """多级缓存测试"""
    
    @pytest.mark.asyncio
    async def test_prompt_cache(self):
        """测试提示词缓存"""
        from efficiency import MultiLevelCache
        
        cache = MultiLevelCache()
        
        # 设置缓存
        key = "prompt:test"
        value = "优化后的提示词"
        await cache.set_prompt(key, value)
        
        # 获取缓存
        result = await cache.get_prompt(key)
        
        assert result == value
    
    @pytest.mark.asyncio
    async def test_model_response_cache(self):
        """测试模型响应缓存"""
        from efficiency import MultiLevelCache
        
        cache = MultiLevelCache()
        
        # 设置缓存
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "user", "content": "今天天气怎么样"}
        ]
        response = {
            "content": "今天天气很好",
            "model": "gpt-3.5-turbo"
        }
        
        await cache.set(str(messages), response)
        
        # 获取缓存
        result = await cache.get(str(messages))
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_tool_cache(self):
        """测试工具缓存"""
        from efficiency import MultiLevelCache
        
        cache = MultiLevelCache()
        
        # 设置缓存
        await cache.set("web_search", {"id": "ws001", "description": "搜索"})
        
        # 获取
        result = await cache.get("web_search")
        
        assert result is not None