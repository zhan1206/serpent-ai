"""
SerpentAI Speech-to-Text (STT) 模块
使用 OpenAI Whisper API 或本地 Whisper 模型进行语音识别
支持多种音频格式和流式音频处理
"""
import io
import logging
import base64
from typing import Optional, Union, AsyncGenerator
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field
import aiohttp
import httpx

from core.config import get_settings
from core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class STTModelSize(str, Enum):
    """ Whisper 模型大小 """
    TINY = "tiny"       # ~39M, 英语最优
    BASE = "base"       # ~74M, 英语最优
    SMALL = "small"     # ~244M, 多语言支持提升
    MEDIUM = "medium"   # ~769M, 高准确率
    LARGE = "large"     # ~1550M, 最高准确率
    WHISPER_1 = "whisper-1"  # API 版本


class STTProvider(str, Enum):
    """ STT 提供商 """
    OPENAI = "openai"       # OpenAI Whisper API
    LOCAL = "local"        # 本地 Whisper 模型
    FAL = "fal"          # Fal AI Whisper


class STTConfig(BaseModel):
    """ STT 配置 """
    provider: STTProvider = STTProvider.OPENAI
    model: STTModelSize = STTModelSize.WHISPER_1
    language: Optional[str] = Field(None, description="语言代码，如 'zh', 'en'")
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    response_format: str = Field("json", description="返回格式: json, text, verbose_json, vtt")
    api_key: Optional[str] = None
    api_base: str = "https://api.openai.com/v1"


class STTResult(BaseModel):
    """ STT 识别结果 """
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None
    words: Optional[list] = None


class SpeechToText:
    """
    语音识别服务
    支持 OpenAI Whisper API 和本地 Whisper 模型
    """
    
    def __init__(self, config: Optional[STTConfig] = None):
        self.config = config or STTConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def recognize(
        self,
        audio_data: Union[bytes, io.BytesIO, str],
        language: Optional[str] = None,
        model: Optional[str] = None,
        response_format: Optional[str] = None
    ) -> STTResult:
        """
        识别音频
        
        Args:
            audio_data: 音频数据（bytes、BytesIO 或 base64 编码的字符串）
            language: 语言代码（覆盖配置）
            model: 模型名称（覆盖配置）
            response_format: 返回格式（覆盖配置）
        
        Returns:
            STTResult: 识别结果
        """
        config = self.config
        language = language or config.language
        model = model or config.model.value
        response_format = response_format or config.response_format
        
        # 处理输入数据
        if isinstance(audio_data, str):
            # Base64 编码的音频
            audio_bytes = base64.b64decode(audio_data)
        elif isinstance(audio_data, io.BytesIO):
            audio_bytes = audio_data.getvalue()
        else:
            audio_bytes = audio_data
        
        logger.info(f"开始语音识别 | 音频大小: {len(audio_bytes)} bytes | 模型: {model}")
        
        if config.provider == STTProvider.OPENAI:
            return await self._recognize_openai(
                audio_bytes,
                language=language,
                model=model,
                response_format=response_format
            )
        elif config.provider == STTProvider.LOCAL:
            return await self._recognize_local(
                audio_bytes,
                language=language,
                model=model
            )
        else:
            raise ValueError(f"不支持的提供商: {config.provider}")
    
    async def _recognize_openai(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        model: str = "whisper-1",
        response_format: str = "json"
    ) -> STTResult:
        """使用 OpenAI Whisper API 识别"""
        config = self.config
        
        # 构建请求
        url = f"{config.api_base}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {config.api_key or settings.OPENAI_API_KEY}"
        }
        
        form_data = aiohttp.FormData()
        form_data.add_field(
            "file",
            audio_bytes,
            filename="audio.wav",
            content_type="audio/wav"
        )
        form_data.add_field("model", model)
        if language:
            form_data.add_field("language", language)
        form_data.add_field("response_format", response_format)
        form_data.add_field("temperature", str(config.temperature))
        
        session = await self._get_session()
        
        try:
            async with session.post(url, headers=headers, data=form_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Whisper API 错误: {resp.status} - {error_text}")
                
                if response_format == "verbose_json":
                    result = await resp.json()
                    return STTResult(
                        text=result.get("text", ""),
                        language=result.get("language"),
                        duration=result.get("duration"),
                        words=result.get("words")
                    )
                elif response_format == "json":
                    result = await resp.json()
                    return STTResult(
                        text=result.get("text", ""),
                        language=result.get("language")
                    )
                else:
                    # text 或 vtt
                    text = await resp.text()
                    return STTResult(text=text)
        
        except aiohttp.ClientError as e:
            logger.error(f"Whisper API 请求失败: {e}")
            raise
    
    async def _recognize_local(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        model: str = "base"
    ) -> STTResult:
        """使用本地 Whisper 模型识别"""
        try:
            import whisper
        except ImportError:
            raise ImportError("请安装 whisper: pip install openai-whisper")
        
        # 加载模型（缓存）
        if not hasattr(self, "_local_model"):
            logger.info(f"加载本地 Whisper 模型: {model}")
            self._local_model = whisper.load_model(model)
        
        # 将音频写入临时文件
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            # 识别
            result = self._local_model.transcribe(
                tmp_path,
                language=language,
                temperature=self.config.temperature
            )
            
            return STTResult(
                text=result["text"],
                language=result.get("language")
            )
        finally:
            os.unlink(tmp_path)
    
    async def recognize_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: Optional[str] = None
    ) -> AsyncGenerator[STTResult, None]:
        """
        流式识别（连续音频流）
        
        Args:
            audio_stream: 音频数据流
            language: 语言代码
        
        Yields:
            STTResult: 识别结果
        """
        buffer = b""
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # 简单分块：在静默处分割（实际应用需要 VAD）
            if len(buffer) > 10000:  # 约 1 秒音频
                result = await self.recognize(
                    buffer,
                    language=language
                )
                if result.text.strip():
                    yield result
                buffer = b""
        
        # 处理剩余数据
        if buffer:
            result = await self.recognize(buffer, language=language)
            if result.text.strip():
                yield result
    
    def detect_language(self, audio_data: bytes) -> Optional[str]:
        """
        检测音频中的语言
        使用 Whisper 的语言检测功能
        """
        try:
            import whisper
        except ImportError:
            return None
        
        if not hasattr(self, "_local_model"):
            model_size = self.config.model.value
            if model_size == "whisper-1":
                model_size = "base"
            self._local_model = whisper.load_model(model_size)
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # 加载音频
            audio = whisper.load_audio(tmp_path)
            audio = whisper.pad_or_trim(audio)
            
            # 编码
           mel = whisper.log_mel_spectrogram(audio, n_fft=self._local_model.n_mels).to(
                self._local_model.device
            )
            
            # 预测语言
            _, probs = self._local_model.detect_language(mel)
            detected_lang = max(probs, key=probs.get)
            
            logger.info(f"检测到语言: {detected_lang} (概率: {probs[detected_lang]:.2f})")
            return detected_lang
        
        finally:
            os.unlink(tmp_path)


# 全局 STT 服务
_stt_service: Optional[SpeechToText] = None


def get_stt_service(config: Optional[STTConfig] = None) -> SpeechToText:
    """获取全局 STT 服务"""
    global _stt_service
    if _stt_service is None:
        _stt_service = SpeechToText(config)
    return _stt_service