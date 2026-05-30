"""
SerpentAI 字节豆包(Doubao)模型适配器
基于Ark API（兼容OpenAI格式）
支持：doubao-pro, doubao-lite等
"""
import logging
import time
from typing import List, Dict, Any, Optional

from backend.models.base_model import BaseModelAdapter, Message, ModelResponse

logger = logging.getLogger(__name__)


class DoubaoAdapter(BaseModelAdapter):
    """字节豆包模型适配器（Ark API，OpenAI兼容格式）"""

    PRICING = {
        "doubao-pro-32k": {"input": 0.0008, "output": 0.002},
        "doubao-pro-128k": {"input": 0.005, "output": 0.009},
        "doubao-lite-32k": {"input": 0.0003, "output": 0.0006},
        "doubao-lite-128k": {"input": 0.001, "output": 0.002},
    }

    CONTEXT_LENGTHS = {
        "doubao-pro-32k": 32768,
        "doubao-pro-128k": 131072,
        "doubao-lite-32k": 32768,
        "doubao-lite-128k": 131072,
    }

    def __init__(self, model_name: str = "doubao-pro-32k", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name, config)
        self.client = None
        self.api_key = None
        self.base_url = None

    def initialize(self) -> bool:
        try:
            import os
            self.api_key = self.config.get("api_key") or os.getenv("DOUBAO_API_KEY", "")
            self.base_url = self.config.get("base_url") or os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
            if not self.api_key:
                logger.warning("Doubao API密钥未配置")
                return False
            try:
                try:
    import openai
except ImportError:
    openai = None
                self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                logger.error("需要openai库来调用Doubao Ark API")
                return False
            self.is_initialized = True
            logger.info(f"Doubao适配器初始化成功: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Doubao初始化失败: {e}")
            return False

    def generate(self, messages: List[Message], temperature: float = 0.7,
                 max_tokens: Optional[int] = None, tools: Optional[List[Dict]] = None,
                 stream: bool = False) -> ModelResponse:
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Doubao适配器未初始化")
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        params = {"model": self.model_name, "messages": openai_messages, "temperature": temperature}
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        start = time.time()
        try:
            response = self.client.chat.completions.create(**params, stream=False)
            content = response.choices[0].message.content or ""
            inp = getattr(response.usage, 'prompt_tokens', 0) or 0
            out = getattr(response.usage, 'completion_tokens', 0) or 0
            latency = int((time.time() - start) * 1000)
            return ModelResponse(content=content, model=self.model_name, input_tokens=inp,
                                 output_tokens=out, total_tokens=inp + out,
                                 cost=self._estimate_cost(inp, out), latency_ms=latency,
                                 metadata={"provider": "doubao"})
        except Exception as e:
            logger.error(f"Doubao生成失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 1.5)

    def get_model_info(self) -> Dict[str, Any]:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.001, "output": 0.002})
        ctx = next((v for k, v in self.CONTEXT_LENGTHS.items() if k in self.model_name), 32768)
        return {"name": self.model_name, "provider": "doubao", "context_length": ctx,
                "pricing": pricing, "supports_tools": True, "supports_streaming": True, "initialized": self.is_initialized}

    def _estimate_cost(self, inp: int, out: int) -> float:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.001, "output": 0.002})
        return (inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"]
