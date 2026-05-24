"""
SerpentAI 深度求索(DeepSeek)模型适配器
兼容OpenAI API格式
支持：deepseek-chat, deepseek-coder等
"""
import logging
import time
from typing import List, Dict, Any, Optional

from backend.models.base_model import BaseModelAdapter, Message, ModelResponse

logger = logging.getLogger(__name__)


class DeepSeekAdapter(BaseModelAdapter):
    """深度求索模型适配器"""

    PRICING = {
        "deepseek-chat": {"input": 0.001, "output": 0.002},
        "deepseek-coder": {"input": 0.001, "output": 0.002},
        "deepseek-reasoner": {"input": 0.004, "output": 0.016},
    }

    CONTEXT_LENGTHS = {
        "deepseek-chat": 65536,
        "deepseek-coder": 16384,
        "deepseek-reasoner": 65536,
    }

    def __init__(self, model_name: str = "deepseek-chat", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name, config)
        self.client = None

    def initialize(self) -> bool:
        try:
            import os
            api_key = self.config.get("api_key") or os.getenv("DEEPSEEK_API_KEY", "")
            base_url = self.config.get("base_url") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            if not api_key:
                logger.warning("DeepSeek API密钥未配置")
                return False
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                logger.error("需要openai库来调用DeepSeek API")
                return False
            self.is_initialized = True
            logger.info(f"DeepSeek适配器初始化成功: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"DeepSeek初始化失败: {e}")
            return False

    def generate(self, messages: List[Message], temperature: float = 0.7,
                 max_tokens: Optional[int] = None, tools: Optional[List[Dict]] = None,
                 stream: bool = False) -> ModelResponse:
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("DeepSeek适配器未初始化")
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        params = {"model": self.model_name, "messages": openai_messages, "temperature": temperature}
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
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
                                 metadata={"provider": "deepseek"})
        except Exception as e:
            logger.error(f"DeepSeek生成失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 1.4)

    def get_model_info(self) -> Dict[str, Any]:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.001, "output": 0.002})
        ctx = next((v for k, v in self.CONTEXT_LENGTHS.items() if k in self.model_name), 65536)
        return {"name": self.model_name, "provider": "deepseek", "context_length": ctx,
                "pricing": pricing, "supports_tools": True, "supports_streaming": True, "initialized": self.is_initialized}

    def _estimate_cost(self, inp: int, out: int) -> float:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.001, "output": 0.002})
        return (inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"]
