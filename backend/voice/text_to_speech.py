"""
SerpentAI Text-to-Speech (TTS) 模块
使用 Edge TTS、OpenAI TTS 等多种提供商进行语音合成
支持中文、英语等多种语言
"""
import io
import logging
import json
import base64
from typing import Optional, AsyncGenerator, Union
from enum import Enum
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field
import aiohttp
import httpx

from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TTSProvider(str, Enum):
    """ TTS 提供商 """
    EDGE = "edge"       # Microsoft Edge TTS (免费，高质量)
    OPENAI = "openai"   # OpenAI TTS API
    ELEVENLABS = "elevenlabs"  # ElevenLabs TTS


class TTSVoice(str, Enum):
    """ 可用语音 """
    # Edge TTS 语音
    ZH_CN_XIAOXIAO = "zh-CN-XiaoxiaoNeural"     # 中文女声
    ZH_CN_YUNQI = "zh-CN-YunxiNeural"          # 中文男声
    ZH_CN_YUNJIA = "zh-CN-YunjiaoNeural"        # 中文女声
    ZH_CN_SHAOLING = "zh-CN-ShaolingNeural"    # 中文男声
    EN_US_JENNY = "en-US-JennyNeural"         # 英语女声
    EN_US_Guy = "en-US-GuyNeural"            # 英语男声
    
    # OpenAI 语音
    OPENAI_TTS_1 = "tts-1"
    OPENAI_TTS_1_HD = "tts-1-hd"
    
    # ElevenLabs 语音
    ELEVENLABS_RACHEL = "rachel"
    ELEVENLABS_CLARKE = "clarke"


class TTSConfig(BaseModel):
    """ TTS 配置 """
    provider: TTSProvider = TTSProvider.EDGE
    voice: TTSVoice = TTSVoice.ZH_CN_XIAOXIAO
    language: Optional[str] = Field(None, description="语言代码")
    speed: float = Field(1.0, ge=0.25, le=4.0)
    pitch: float = Field(0.0, ge=-50.0, le=50.0)
    volume: float = Field(1.0, ge=0.0, le=2.0)
    api_key: Optional[str] = None
    api_base: str = "https://api.openai.com/v1"


class TTSResult(BaseModel):
    """ TTS 结果 """
    audio: bytes
    audio_base64: Optional[str] = None
    format: str = "mp3"
    duration: Optional[float] = None


class TextToSpeech:
    """
    语音合成服务
    支持 Edge TTS（免费高质量）和 OpenAI TTS API
    """
    
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
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
    
    async def speak(
        self,
        text: str,
        voice: Optional[Union[TTSVoice, str]] = None,
        speed: Optional[float] = None,
        pitch: Optional[float] = None,
        output_format: Optional[str] = None
    ) -> TTSResult:
        """
        合成语音
        
        Args:
            text: 要合成文本
            voice: 语音选择（覆盖配置）
            speed: 语速（覆盖配置）
            pitch: 音调（覆盖配置）
            output_format: 输出格式
        
        Returns:
            TTSResult: 音频结果
        """
        config = self.config
        voice = voice or config.voice
        speed = speed or config.speed
        pitch = pitch or config.pitch
        
        logger.info(f"开始语音合成 | 提供商: {config.provider} | 文本长度: {len(text)}")
        
        if config.provider == TTSProvider.EDGE:
            return await self._speak_edge(
                text,
                voice=voice.value if isinstance(voice, TTSVoice) else voice,
                speed=speed,
                pitch=pitch
            )
        elif config.provider == TTSProvider.OPENAI:
            return await self._speak_openai(
                text,
                voice=voice.value if isinstance(voice, TTSVoice) else voice,
                speed=speed
            )
        elif config.provider == TTSProvider.ELEVENLABS:
            return await self._speak_elevenlabs(
                text,
                voice=voice.value if isinstance(voice, TTSVoice) else voice
            )
        else:
            raise ValueError(f"不支持的提供商: {config.provider}")
    
    async def _speak_edge(
        self,
        text: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        speed: float = 1.0,
        pitch: float = 0.0
    ) -> TTSResult:
        """使用 Edge TTS 合成语音"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("请安装 edge-tts: pip install edge-tts")
        
        # 构建 SSML（如果需要调整语音参数）
        rate = f"{speed:.0%}"  # 如 "100%", "150%"
        pitch_str = f"+{pitch:.0f}Hz" if pitch >= 0 else f"{pitch:.0f}Hz"
        
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch_str)
        
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        logger.info(f"Edge TTS 合成完成 | 音频大小: {len(audio_data)} bytes")
        
        return TTSResult(
            audio=audio_data,
            format="mp3"
        )
    
    async def _speak_openai(
        self,
        text: str,
        voice: str = "tts-1",
        speed: float = 1.0
    ) -> TTSResult:
        """使用 OpenAI TTS API 合成语音"""
        config = self.config
        
        # 将语速转换为 API 格式 (0.25-4.0 -> 0.25-2.0)
        api_speed = min(max(speed, 0.25), 2.0)
        
        url = f"{config.api_base}/audio/speech"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key or settings.OPENAI_API_KEY}"
        }
        
        payload = {
            "model": "tts-1",
            "voice": voice,
            "input": text,
            "speed": api_speed
        }
        
        session = await self._get_session()
        
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI TTS API 错误: {resp.status} - {error_text}")
            
            audio_data = await resp.read()
        
        logger.info(f"OpenAI TTS 合成完成 | 音频大小: {len(audio_data)} bytes")
        
        return TTSResult(
            audio=audio_data,
            format="mp3"
        )
    
    async def _speak_elevenlabs(
        self,
        text: str,
        voice: str = "rachel"
    ) -> TTSResult:
        """使用 ElevenLabs TTS 合成语音"""
        config = self.config
        api_key = config.api_key or settings.ELEVENLABS_API_KEY
        
        if not api_key:
            raise ValueError("需要设置 ELEVENLABS_API_KEY")
        
        # 获取语音 ID
        voice_id = self._get_elevenlabs_voice_id(voice)
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 1.0
            }
        }
        
        session = await self._get_session()
        
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"ElevenLabs API 错误: {resp.status} - {error_text}")
            
            audio_data = await resp.read()
        
        logger.info(f"ElevenLabs TTS 合成完成 | 音频大小: {len(audio_data)} bytes")
        
        return TTSResult(
            audio=audio_data,
            format="mp3"
        )
    
    def _get_elevenlabs_voice_id(self, voice: str) -> str:
        """获取 ElevenLabs 语音 ID 映射"""
        voice_map = {
            "rachel": "21m00Tcm4TlvDq8ikWAM",
            "clarke": "2EiwWn06I2O4DdjZs7cY",
            "domi": "AZRFZHN3PlNP21euIVR0",
            "gdraz": "jsCjWAjDI3c5dFeoZ9uE",
            "harry": "jsCjWAjDI3c5dFeoZ9uE",
        }
        return voice_map.get(voice, voice)
    
    async def speak_stream(
        self,
        text: str,
        voice: Optional[Union[TTSVoice, str]] = None,
        speed: Optional[float] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        流式语音合成（边合成边返回）
        
        注意：目前仅 Edge TTS 支持流式输出
        """
        config = self.config
        
        if config.provider != TTSProvider.EDGE:
            # 非 Edge TTS，转换为一次性返回
            result = self.speak(text, voice=voice, speed=speed)
            yield result.audio
            return
        
        try:
            import edge_tts
        except ImportError:
            raise ImportError("请安装 edge-tts: pip install edge-tts")
        
        voice = (voice or config.voice).value if isinstance(voice, TTSVoice) else voice
        rate = f"{speed or config.speed:.0%}"
        
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]


# 全局 TTS 服务
_tts_service: Optional[TextToSpeech] = None


def get_tts_service(config: Optional[TTSConfig] = None) -> TextToSpeech:
    """获取全局 TTS 服务"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TextToSpeech(config)
    return _tts_service