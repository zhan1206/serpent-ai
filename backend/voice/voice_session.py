"""
SerpentAI Voice Session Management 模块
管理语音会话的状态机、会话上下文和音频缓冲
状态流转: idle -> listening -> processing -> speaking -> idle
"""
import logging
import uuid
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from pydantic import BaseModel, Field

from backend.core.logging_config import get_logger

logger = get_logger(__name__)


class VoiceState(str, Enum):
    """ 语音会话状态 """
    IDLE = "idle"           # 空闲
    LISTENING = "listening" # 监听中
    PROCESSING = "processing"  # 处理中
    SPEAKING = "speaking"   # 说话中
    WAITING = "waiting"     # 等待响应


class VoiceMode(str, Enum):
    """ 语音交互模式 """
    PTT = "ptt"             # 按住说话 (Push-to-Talk)
    VAD = "vad"            # 语音活动检测
    WAKE = "wake"          # 唤醒词模式


@dataclass
class ConversationContext:
    """ 对话上下文 """
    session_id: str
    history: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.history.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def add_assistant_message(self, content: str):
        """添加助手消息"""
        self.history.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
    
    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """获取最近的对话历史"""
        return self.history[-limit:]


class VoiceSessionConfig(BaseModel):
    """ 语音会话配置 """
    mode: VoiceMode = VoiceMode.PTT
    stt_provider: str = "openai"
    tts_provider: str = "edge"
    stt_model: str = "whisper-1"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    language: Optional[str] = "zh"
    auto_tts: bool = True
    vad_threshold: float = 0.02
    vad_silence_duration: float = 1.5
    max_audio_duration: float = 30.0


class VoiceSession:
    """
    语音会话管理
    管理语音交互的状态机、音频缓冲和对话上下文
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[VoiceSessionConfig] = None
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.config = config or VoiceSessionConfig()
        
        self.state = VoiceState.IDLE
        self.audio_buffer: bytes = b""
        self.context = ConversationContext(session_id=self.session_id)
        
        # STT 和 TTS 服务
        self._stt_service = None
        self._tts_service = None
        self._wake_detector = None
        
        # 回调函数
        self._on_state_change: Optional[callable] = None
        self._on_result: Optional[callable] = None
        
        # 统计信息
        self.stats = {
            "requests_count": 0,
            "total_audio_duration": 0.0,
            "errors": 0
        }
    
    def set_state(self, new_state: VoiceState):
        """设置状态"""
        old_state = self.state
        self.state = new_state
        logger.info(f"语音会话状态变更 | session: {self.session_id} | {old_state.value} -> {new_state.value}")
        
        if self._on_state_change:
            self._on_state_change(old_state, new_state)
    
    async def start_listening(self):
        """开始监听"""
        self.set_state(VoiceState.LISTENING)
        self.audio_buffer = b""
    
    async def stop_listening(self) -> bytes:
        """停止监听，返回音频数据"""
        audio_data = self.audio_buffer
        self.audio_buffer = b""
        self.set_state(VoiceState.PROCESSING)
        return audio_data
    
    def append_audio(self, audio_chunk: bytes):
        """追加音频数据"""
        self.audio_buffer += audio_chunk
        
        # 检查最大时长
        if self.config.max_audio_duration > 0:
            # 估算音频时长（假设 16kHz, 16bit）
            duration = len(self.audio_buffer) / (16000 * 2)
            if duration > self.config.max_audio_duration:
                logger.warning(f"音频时长超过限制: {duration:.1f}s > {self.config.max_audio_duration}s")
    
    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        处理音频（STT -> Agent -> TTS）
        
        Returns:
            Dict 包含 text, response, audio 等字段
        """
        from .speech_to_text import get_stt_service, STTConfig, STTProvider
        from .text_to_speech import get_tts_service, TTSConfig, TTSProvider
        
        self.set_state(VoiceState.PROCESSING)
        self.stats["requests_count"] += 1
        
        result = {
            "success": False,
            "text": "",
            "response": "",
            "audio": None,
            "error": None
        }
        
        try:
            # 1. 语音识别 (STT)
            logger.info("开始语音识别...")
            stt_config = STTConfig(
                provider=STTProvider(self.config.stt_provider),
                model=self.config.stt_model,
                language=self.config.language
            )
            stt_service = get_stt_service(stt_config)
            
            stt_result = await stt_service.recognize(audio_data)
            result["text"] = stt_result.text
            
            if not stt_result.text.strip():
                logger.warning("未检测到语音内容")
                self.set_state(VoiceState.IDLE)
                return result
            
            logger.info(f"语音识别完成: {stt_result.text[:50]}...")
            
            # 2. 调用 Agent
            logger.info("调用 Agent 处理...")
            agent_response = await self._call_agent(stt_result.text)
            result["response"] = agent_response
            
            # 保存到对话上下文
            self.context.add_user_message(stt_result.text)
            self.context.add_assistant_message(agent_response)
            
            # 3. 语音合成 (TTS)
            if self.config.auto_tts and agent_response:
                logger.info("开始语音合成...")
                tts_config = TTSConfig(
                    provider=TTSProvider(self.config.tts_provider),
                    voice=self.config.tts_voice,
                    language=self.config.language
                )
                tts_service = get_tts_service(tts_config)
                
                tts_result = await tts_service.speak(agent_response)
                result["audio"] = tts_result.audio
            
            result["success"] = True
            self.set_state(VoiceState.SPEAKING if result["audio"] else VoiceState.IDLE)
            
        except Exception as e:
            logger.error(f"语音处理失败: {e}")
            result["error"] = str(e)
            self.stats["errors"] += 1
            self.set_state(VoiceState.IDLE)
        
        return result
    
    async def _call_agent(self, text: str) -> str:
        """调用 Agent 获取响应"""
        # 导入 Agent
        try:
            from backend.agent import get_agent, AgentConfig
            
            agent = get_agent(AgentConfig())
            
            # 运行 Agent
            result = await agent.run(
                session_id=self.session_id,
                user_message=text
            )
            
            return result.get("response", str(result))
        
        except ImportError:
            # 如果 Agent 模块不可用，返回简单响应
            logger.warning("Agent 模块不可用，使用简单响应")
            return f"收到消息: {text}"
    
    async def speak(self, text: str) -> Optional[bytes]:
        """合成并返回语音"""
        from .text_to_speech import get_tts_service, TTSConfig, TTSProvider
        
        self.set_state(VoiceState.SPEAKING)
        
        try:
            tts_config = TTSConfig(
                provider=TTSProvider(self.config.tts_provider),
                voice=self.config.tts_voice,
                language=self.config.language
            )
            tts_service = get_tts_service(tts_config)
            
            result = await tts_service.speak(text)
            return result.audio
        
        finally:
            self.set_state(VoiceState.IDLE)
    
    def get_status(self) -> Dict[str, Any]:
        """获取会话状态"""
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "mode": self.config.mode.value,
            "config": self.config.model_dump(),
            "stats": self.stats,
            "history_count": len(self.context.history)
        }
    
    def reset(self):
        """重置会话"""
        self.state = VoiceState.IDLE
        self.audio_buffer = b""
        self.stats = {
            "requests_count": 0,
            "total_audio_duration": 0.0,
            "errors": 0
        }
        logger.info(f"会话已重置: {self.session_id}")
    
    def set_callbacks(
        self,
        on_state_change: Optional[callable] = None,
        on_result: Optional[callable] = None
    ):
        """设置回调函数"""
        self._on_state_change = on_state_change
        self._on_result = on_result


# 全局会话管理
_sessions: Dict[str, VoiceSession] = {}


def get_voice_session(session_id: str) -> VoiceSession:
    """获取或创建语音会话"""
    if session_id not in _sessions:
        _sessions[session_id] = VoiceSession(session_id)
    return _sessions[session_id]


def list_voice_sessions() -> List[str]:
    """列出所有会话 ID"""
    return list(_sessions.keys())


def remove_voice_session(session_id: str):
    """移除会话"""
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info(f"移除会话: {session_id}")