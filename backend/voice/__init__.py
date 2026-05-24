"""
SerpentAI Voice Interaction Module
语音交互模块，提供语音转文字（STT）、文字转语音（TTS）功能
支持多种提供商：OpenAI Whisper、Edge TTS、OpenAI TTS
"""
import logging
from typing import Optional

# 配置日志
from backend.core.logging_config import get_logger
logger = get_logger(__name__)

# 导出语音配置
from .voice_session import VoiceSession, get_voice_session

# 导出语音路由
from .voice_router import router as voice_router

__all__ = [
    "VoiceSession",
    "get_voice_session",
    "voice_router",
]