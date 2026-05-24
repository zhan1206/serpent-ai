"""
SerpentAI Token计算器
精确计算输入输出Token消耗
支持tiktoken（OpenAI模型）和字符估算
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 尝试导入tiktoken
_tiktoken_available = False
_encoding_cache: Dict = {}
try:
    import tiktoken
    _tiktoken_available = True
except ImportError:
    logger.debug("tiktoken未安装，将使用字符估算")

# 模型到tiktoken编码的映射
_MODEL_ENCODING_MAP = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "o1-preview": "o200k_base",
    "o1-mini": "o200k_base",
    "text-embedding-ada-002": "p50k_base",
}

# 模型每字符Token比率估算（非OpenAI模型）
_CHAR_TOKEN_RATIO = {
    "claude": 1.25,       # Claude系列
    "llama": 1.30,        # Llama系列
    "qwen": 1.50,        # 通义千问（中文优化）
    "deepseek": 1.40,    # DeepSeek
    "doubao": 1.50,      # 豆包（中文优化）
    "wenxin": 1.50,      # 文心（中文优化）
    "gemini": 1.20,      # Gemini
    "default": 1.30,     # 默认
}


class TokenCounter:
    """
    Token计算器
    
    优先使用tiktoken精确计算（OpenAI模型），
    其他模型使用字符数/比率估算。
    """

    def __init__(self):
        self._total_input = 0
        self._total_output = 0
        self._call_count = 0

    @staticmethod
    def count(text: str, model_name: str = "gpt-4o") -> int:
        """
        计算文本的Token数
        
        Args:
            text: 输入文本
            model_name: 模型名称（用于选择编码器）
            
        Returns:
            int: Token数量
        """
        if not text:
            return 0

        if _tiktoken_available:
            encoding_name = _MODEL_ENCODING_MAP.get(model_name, "cl100k_base")
            if encoding_name not in _encoding_cache:
                try:
                    _encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
                except Exception:
                    _encoding_cache[encoding_name] = None

            encoding = _encoding_cache.get(encoding_name)
            if encoding:
                try:
                    return len(encoding.encode(text))
                except Exception:
                    pass

        # 回退到字符估算
        ratio = _CHAR_TOKEN_RATIO.get("default")
        model_lower = model_name.lower()
        for key, r in _CHAR_TOKEN_RATIO.items():
            if key in model_lower:
                ratio = r
                break

        return max(1, int(len(text) / ratio))

    @staticmethod
    def count_messages(messages: list, model_name: str = "gpt-4o") -> int:
        """
        计算消息列表的总Token数
        
        Args:
            messages: Message对象列表
            model_name: 模型名称
            
        Returns:
            int: 总Token数
        """
        total = 0
        for msg in messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            total += TokenCounter.count(content, model_name)
            # 消息格式开销（role, separators等）
            total += 4
        # 对话格式开销
        total += 2
        return total

    def record(self, input_tokens: int, output_tokens: int):
        """记录Token使用"""
        self._total_input += input_tokens
        self._total_output += output_tokens
        self._call_count += 1

    @property
    def total_input_tokens(self) -> int:
        return self._total_input

    @property
    def total_output_tokens(self) -> int:
        return self._total_output

    @property
    def total_tokens(self) -> int:
        return self._total_input + self._total_output

    @property
    def call_count(self) -> int:
        return self._call_count

    def get_stats(self) -> Dict[str, int]:
        """获取Token使用统计"""
        return {
            "total_input_tokens": self._total_input,
            "total_output_tokens": self._total_output,
            "total_tokens": self.total_tokens,
            "call_count": self._call_count,
        }

    def reset(self):
        """重置统计"""
        self._total_input = 0
        self._total_output = 0
        self._call_count = 0


# 全局Token计数器
_global_counter: Optional[TokenCounter] = None


def get_global_counter() -> TokenCounter:
    """获取全局Token计数器"""
    global _global_counter
    if _global_counter is None:
        _global_counter = TokenCounter()
    return _global_counter
