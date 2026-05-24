"""
SerpentAI 阿里通义千问(Qwen)模型适配器
基于DashScope API（兼容OpenAI格式）
支持：qwen-turbo, qwen-plus, qwen-max等
"""
import logging
import time
from typing import List, Dict, Any, Optional

from models.base_model import BaseModelAdapter, Message, ModelResponse

logger = logging.getLogger(__name__)


class QwenAdapter(BaseModelAdapter):
    """阿里通义千问模型适配器"""

    PRICING = {
        "qwen-turbo": {"input": 0.0003, "output": 0.0006},
        "qwen-plus": {"input": 0.002, "output": 0.006},
        "qwen-max": {"input": 0.02, "output": 0.06},
        "qwen-long": {"input": 0.0005, "output": 0.002},
    }

    CONTEXT_LENGTHS = {
        "qwen-turbo": 131072,
        "qwen-plus": 131072,
        "qwen-max": 32768,
        "qwen-long": 1048576,
    }

    def __init__(self, model_name: str = "qwen-turbo", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name, config)
        self.client = None

    def initialize(self) -> bool:
        try:
            import os
            api_key = self.config.get("api_key") or os.getenv("DASHSCOPE_API_KEY", "")
            base_url = self.config.get("base_url") or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            if not api_key:
                logger.warning("DashScope API密钥未配置")
                return False
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                logger.error("需要openai库来调用Qwen API")
                return False
            self.is_initialized = True
            logger.info(f"Qwen适配器初始化成功: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Qwen初始化失败: {e}")
            return False

    def generate(self, messages: List[Message], temperature: float = 0.7,
                 max_tokens: Optional[int] = None, tools: Optional[List[Dict]] = None,
                 stream: bool = False) -> ModelResponse:
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Qwen适配器未初始化")
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        params = {"model": self.model_name, "messages": openai_messages, "temperature": temperature}
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = tools
        start = time.time()
        try:
            resp = self.client.chat.completions.create(**params, stream=False)
            content = resp.choices[0].message.content or ""
            inp = getattr(resp.usage, 'prompt_tokens', 0) or 0
            out = getattr(resp.usage, 'completion_tokens', 0) or 0
            latency = int((time.time() - start) * 1000)
            return ModelResponse(content=content, model=self.model_name, input_tokens=inp,
                                 output_tokens=out, total_tokens=inp + out,
                                 cost=self._estimate_cost(inp, out), latency_ms=latency,
                                 metadata={"provider": "qwen"})
        except Exception as e:
            logger.error(f"Qwen生成失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 1.5)

    def get_model_info(self) -> Dict[str, Any]:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.002, "output": 0.006})
        ctx = next((v for k, v in self.CONTEXT_LENGTHS.items() if k in self.model_name), 131072)
        return {"name": self.model_name, "provider": "qwen", "context_length": ctx,
                "pricing": pricing, "supports_tools": True, "supports_streaming": True, "initialized": self.is_initialized}

    def _estimate_cost(self, inp: int, out: int) -> float:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.002, "output": 0.006})
        return (inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"]
