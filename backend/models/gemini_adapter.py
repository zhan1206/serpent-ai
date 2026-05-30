"""
SerpentAI Google Gemini模型适配器
基于Google Generative AI SDK
支持：gemini-pro, gemini-1.5-pro, gemini-1.5-flash等
"""
import logging
import time
from typing import List, Dict, Any, Optional

from backend.models.base_model import BaseModelAdapter, Message, ModelResponse

logger = logging.getLogger(__name__)


class GeminiAdapter(BaseModelAdapter):
    """Google Gemini模型适配器"""

    PRICING = {
        "gemini-pro": {"input": 0.00025, "output": 0.0005},
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    }

    CONTEXT_LENGTHS = {
        "gemini-pro": 32768,
        "gemini-1.5-pro": 2097152,
        "gemini-1.5-flash": 1048576,
    }

    def __init__(self, model_name: str = "gemini-1.5-flash", config: Optional[Dict[str, Any]] = None):
        super().__init__(model_name, config)
        self._genai = None
        self._model = None

    def initialize(self) -> bool:
        try:
            import os
            api_key = self.config.get("api_key") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("Google/Gemini API密钥未配置")
                return False
            try:
                import google.generativeai as genai
                self._genai = genai
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(self.model_name)
            except ImportError:
                logger.warning("google-generativeai未安装，尝试OpenAI兼容接口")
                try:
                    try:
    import openai
except ImportError:
    openai = None
                    base_url = self.config.get("base_url") or os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
                    self._openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
                    self._model = None  # 使用OpenAI兼容路径
                except ImportError:
                    logger.error("需要google-generativeai或openai库")
                    return False
            self.is_initialized = True
            logger.info(f"Gemini适配器初始化成功: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Gemini初始化失败: {e}")
            return False

    def generate(self, messages: List[Message], temperature: float = 0.7,
                 max_tokens: Optional[int] = None, tools: Optional[List[Dict]] = None,
                 stream: bool = False) -> ModelResponse:
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError("Gemini适配器未初始化")
        start = time.time()
        try:
            if self._model is not None:
                return self._generate_native(messages, temperature, max_tokens, start)
            else:
                return self._generate_openai_compat(messages, temperature, max_tokens, tools, start)
        except Exception as e:
            logger.error(f"Gemini生成失败: {e}")
            raise

    def _generate_native(self, messages: List[Message], temperature: float,
                         max_tokens: Optional[int], start: float) -> ModelResponse:
        """使用原生Google SDK"""
        history = []
        for msg in messages[:-1]:
            history.append({"role": "user" if msg.role == "user" else "model", "parts": [msg.content]})
        last_msg = messages[-1].content if messages else ""
        chat = self._model.start_chat(history=history)
        gen_config = {"temperature": temperature}
        if max_tokens:
            gen_config["max_output_tokens"] = max_tokens
        resp = chat.send_message(last_msg, generation_config=gen_config)
        content = resp.text or ""
        inp_tok = self.count_tokens(" ".join(m.content for m in messages))
        out_tok = self.count_tokens(content)
        latency = int((time.time() - start) * 1000)
        return ModelResponse(content=content, model=self.model_name, input_tokens=inp_tok,
                             output_tokens=out_tok, total_tokens=inp_tok + out_tok,
                             cost=self._estimate_cost(inp_tok, out_tok), latency_ms=latency,
                             metadata={"provider": "gemini", "sdk": "native"})

    def _generate_openai_compat(self, messages: List[Message], temperature: float,
                                max_tokens: Optional[int], tools: Optional[List[Dict]], start: float) -> ModelResponse:
        """使用OpenAI兼容接口"""
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        params = {"model": self.model_name, "messages": openai_messages, "temperature": temperature}
        if max_tokens:
            params["max_tokens"] = max_tokens
        resp = self._openai_client.chat.completions.create(**params, stream=False)
        content = resp.choices[0].message.content or ""
        inp = getattr(resp.usage, 'prompt_tokens', 0) or 0
        out = getattr(resp.usage, 'completion_tokens', 0) or 0
        latency = int((time.time() - start) * 1000)
        return ModelResponse(content=content, model=self.model_name, input_tokens=inp,
                             output_tokens=out, total_tokens=inp + out,
                             cost=self._estimate_cost(inp, out), latency_ms=latency,
                             metadata={"provider": "gemini", "sdk": "openai_compat"})

    def count_tokens(self, text: str) -> int:
        if self._model is not None and self._genai:
            try:
                return self._model.count_tokens(text).total_tokens
            except Exception:
                pass
        return max(1, len(text) // 1.2)

    def get_model_info(self) -> Dict[str, Any]:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.000075, "output": 0.0003})
        ctx = next((v for k, v in self.CONTEXT_LENGTHS.items() if k in self.model_name), 32768)
        return {"name": self.model_name, "provider": "gemini", "context_length": ctx,
                "pricing": pricing, "supports_tools": True, "supports_streaming": True, "initialized": self.is_initialized}

    def _estimate_cost(self, inp: int, out: int) -> float:
        pricing = next((v for k, v in self.PRICING.items() if k in self.model_name), {"input": 0.000075, "output": 0.0003})
        return (inp / 1000) * pricing["input"] + (out / 1000) * pricing["output"]
