"""
Efficiency Engine - 效率引擎
全局Token消耗监控和优化调度

包含6个模块：TokenOptimizer、PromptDistiller、IncrementalContextManager、
SemanticCompressor、OutputCompressor、MultiLevelCache

加速策略：当 Rust 核心模块 (serpent_ai_core) 编译安装后，
TokenOptimizer 自动使用 xxHash/LZ4/Rayon 加速路径，
否则使用纯 Python 实现（功能一致）。
"""

from .token_optimizer import TokenOptimizer
from .prompt_distiller import PromptDistiller
from .incremental_context import IncrementalContextManager
from .semantic_compressor import SemanticCompressor
from .output_compressor import OutputCompressor
from .multi_level_cache import MultiLevelCache

# 全局效率引擎实例
_global_engine = None


def get_global_engine() -> dict:
    """获取全局效率引擎组件"""
    global _global_engine
    
    if _global_engine is None:
        _global_engine = {
            "token_optimizer": TokenOptimizer(),
            "prompt_distiller": PromptDistiller(),
            "context_manager": IncrementalContextManager(),
            "semantic_compressor": SemanticCompressor(),
            "output_compressor": OutputCompressor(),
            "cache": MultiLevelCache()
        }
    
    return _global_engine


# 测试
if __name__ == "__main__":
    engine = get_global_engine()
    
    # 测试Token优化器
    optimizer = engine["token_optimizer"]
    optimizer.record_request(100, 50, 0.001)
    optimizer.record_savings("prompt_distillation_savings", 500)
    print(f"Token optimizer stats: {optimizer.get_stats()}")
    
    # 测试提示词蒸馏
    distiller = engine["prompt_distiller"]
    original = "This is a very long prompt with lots of extra whitespace and unnecessary details " * 10
    distilled = distiller.distill(original)
    print(f"Original length: {len(original)}, Distilled length: {len(distilled)}")
    
    # 测试增量上下文
    context_mgr = engine["context_manager"]
    messages = [{"role": "user", "content": f"Message {i}"} for i in range(20)]
    state_id = context_mgr.save_state("session1", messages)
    incremental = context_mgr.get_incremental_messages("session1", messages + [{"role": "user", "content": "New message"}])
    print(f"State ID: {state_id}, Incremental messages: {len(incremental)}")
    
    # 测试输出压缩
    compressor = engine["output_compressor"]
    output = "This is   a test   output with   extra   whitespace. "
    compressed = compressor.compress(output * 10)
    print(f"Original length: {len(output * 10)}, Compressed length: {len(compressed)}")
    print(f"Compression stats: {compressor.get_stats()}")
    
    # 测试多级缓存
    cache = engine["cache"]
    cache.set("prompt", "key1", "value1")
    value = cache.get("prompt", "key1")
    print(f"Cache test - retrieved: {value}")
    print(f"Cache stats: {cache.get_stats()}")
