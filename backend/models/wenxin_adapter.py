"""
SerpentAI 百度文心一言(Wenxin)模型适配器
基于千帆API（兼容OpenAI格式）
支持：ernie-4.0, ernie-3.5-turbo等
"""
import logging
import time
from typing import List, Dict, Any, Optional

from backend.models.base_model import BaseModelAdapter, Message, ModelResponse

logger = logging.getLogger(__name__)


class WenxinAdapter(BaseModelAdapter):
    """百度文心一言模型适配器"""

    PRICING = {
        "ernie-4.0-8k": {"input": 0.03, "output": 0.09},
        "ernie-4.0-128k": {"input": 0.06, "output": 0.12},
        "ernie-3.5-8k": {"input": 0.0012, "output": 0.0012},
        "ernie-speed-8k": {"input": 0.0, "output": 0.0},
    }

    CONTEXT_LENGTHS = {
        "ernie-4.0-8k": 8192,
        "ernie-4.0-128k": 131072,
        "ernie-3.5-8k": 8192,
        "ernie-speed-8k": 8192,
    }

    # 千帆API模型名映射
    MODEL_MAP = {
        "ernie-4.0": "ernie-4.0-8k",
        "ernie-3.5": "ernie-3.5-8k",
        "ernie-speed": "ernie-speed-8k",
    }

    def __init__(self, model_name: str = "ernie-4.0-8k", config: Optional[Dict[str, Any]] = None):
        actual_name = self.MODEL_MAP.get(model_name, model_name)
        super().__init__(actual_name, config)
        self.client = None

    def initialize(self) -> bool:
        try:
            import os
            api_key = self.config.get("api_key") or os.getenv("QIANFAN_API_KEY", "")
            base_url = self.config.get("base_url") or os.getenv("QIANFAN_BASE_URL", "https://qianfan.baidubce.com/v2")
            if not api_key:
                logger.warning("千帆API密钥未配置")
                return False
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
            except ImportError:
                logger.error("需要openai库来调用千帆API")
                return False
            self.is_initialized = True
            logger.info(f"Wenxin适配器初始化成功: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Wenxin初始化失败: {e}")
            return False

    def generate(self, messages: List[Message], temperature: float = 0.7,
                 max_tokens: Optional[int] = None, tools: Optional[List[Dict]] = None,
                 stream: bool = False) -> ModelResponse:
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Wenxin适配器未初始化")
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        params = {"model": self.model_name, "messages": openai_messages, "temperature": temperature}
        if max_tokens:
            params["max_tokens"] = max_tokens
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
                                 metadata={"provider": "wenxin"})
        except Exception as e:
            logger.error(f"Wenxin生成失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 1.5)

    def get_model_info(self) -> Dict[str, Any]:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.0012, "output": 0.0012})
        ctx = next((v for k, v in self.CONTEXT_LENGTHS.items() if k in self.model_name), 8192)
        return {"name": self.model_name, "provider": "wenxin", "context_length": ctx,
                "pricing": pricing, "supports_tools": True, "supports_streaming": True, "initialized": self.is_initialized}

    def _estimate_cost(self, inp: int, out: int) -> float:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.0012, "output": 0.0012})
        return (inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"]
