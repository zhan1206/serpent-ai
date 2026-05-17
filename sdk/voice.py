"""
SerpentAI SDK - 语音交互模块
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
import base64

from .types import VoiceSession
if TYPE_CHECKING:
    from .client import SerpentAI


class VoiceManager:
    """语音交互管理器"""
    
    def __init__(self, client: "SerpentAI"):
        self._client = client
    
    def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "zh-CN",
        model: str = "whisper-1",
    ) -> str:
        """
        语音转文字
        
        Args:
            audio_data: 音频数据（字节）
            language: 语言
            model: STT模型
        
        Returns:
            str: 识别的文本
        """
        files = {"audio": ("audio.webm", audio_data, "audio/webm")}
        data = {"language": language, "model": model}
        
        result = self._client.post("/api/voice/stt", data=data, json=None)
        return result.get("text", "")
    
    def text_to_speech(
        self,
        text: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        speed: float = 1.0,
    ) -> bytes:
        """
        文字转语音
        
        Args:
            text: 要转换的文本
            voice: 声音名称
            speed: 语速 (0.5-2.0)
        
        Returns:
            bytes: MP3音频数据
        """
        payload = {
            "text": text,
            "voice": voice,
            "speed": speed,
        }
        
        result = self._client.post("/api/voice/tts", json=payload)
        audio_b64 = result.get("audio", "")
        if audio_b64:
            return base64.b64decode(audio_b64)
        return b""
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """列出可用的TTS声音"""
        result = self._client.get("/api/voice/tts/voices")
        return result.get("voices", [])
    
    def voice_chat(
        self,
        audio_data: bytes,
        language: str = "zh-CN",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        语音聊天（STT -> AI -> TTS）
        
        Args:
            audio_data: 音频数据（字节）
            language: 语言
            session_id: 会话ID
        
        Returns:
            dict: 包含 text(识别文本), response(AI响应), audio(语音响应)
        """
        audio_b64 = base64.b64encode(audio_data).decode()
        
        payload = {
            "audio_data": audio_b64,
            "language": language,
            "session_id": session_id or "",
        }
        
        result = self._client.post("/api/voice/chat", json=payload)
        
        # 解码返回的音频
        if result.get("audio"):
            result["audio_bytes"] = base64.b64decode(result["audio"])
        
        return result
    
    def detect_wake_word(
        self,
        audio_data: bytes,
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        唤醒词检测
        
        Args:
            audio_data: 音频数据
            threshold: 置信度阈值
        
        Returns:
            dict: {detected: bool, wake_word: str, confidence: float}
        """
        files = {"audio": ("audio.webm", audio_data, "audio/webm")}
        data = {"threshold": threshold}
        
        return self._client.post("/api/voice/wake", data=data, json=None)
    
    def list_wake_words(self) -> List[str]:
        """列出可用的唤醒词"""
        result = self._client.get("/api/voice/wake/words")
        return result.get("wake_words", [])
    
    def get_session(self, session_id: str) -> VoiceSession:
        """获取语音会话"""
        result = self._client.get(f"/api/voice/session/{session_id}")
        return VoiceSession.from_dict(result)
    
    def list_sessions(self) -> List[VoiceSession]:
        """列出所有语音会话"""
        result = self._client.get("/api/voice/sessions")
        return [VoiceSession.from_dict(s) for s in result.get("sessions", [])]
    
    def delete_session(self, session_id: str) -> bool:
        """删除语音会话"""
        result = self._client.delete(f"/api/voice/session/{session_id}")
        return result.get("deleted", False)
    
    def get_status(self) -> Dict[str, Any]:
        """获取语音服务状态"""
        return self._client.get("/api/voice/status")


class AsyncVoiceManager:
    """异步语音管理器"""
    
    def __init__(self, client):
        self._client = client
    
    async def speech_to_text(self, audio_data: bytes, **kwargs) -> str:
        result = await self._client.post("/api/voice/stt", json={"audio": audio_data, **kwargs})
        return result.get("text", "")
    
    async def voice_chat(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        result = await self._client.post("/api/voice/chat", json={"audio_data": audio_data, **kwargs})
        return result
