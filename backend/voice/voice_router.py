"""
SerpentAI Voice Router
语音交互 API 路由
"""
import logging
from typing import Optional, List
import base64

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel

from .speech_to_text import (
    SpeechToText, STTConfig, STTProvider,
    STTModelSize, get_stt_service
)
from .text_to_speech import (
    TextToSpeech, TTSConfig, TTSProvider,
    TTSVoice, get_tts_service
)
from .voice_session import (
    VoiceSession, VoiceSessionConfig,
    VoiceMode, get_voice_session,
    list_voice_sessions, remove_voice_session
)
from .wake_word import (
    WakeWordDetector, WakeConfig, WakeMethod,
    get_wake_detector
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["语音交互"])


# ==================== 请求/响应模型 ====================

class STTRequest(BaseModel):
    """ 语音识别请求 """
    provider: Optional[str] = "openai"
    model: Optional[str] = "whisper-1"
    language: Optional[str] = None


class STTResponse(BaseModel):
    """ 语音识别响应 """
    success: bool
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


class TTSRequest(BaseModel):
    """ 语音合成请求 """
    text: str
    provider: Optional[str] = "edge"
    voice: Optional[str] = "zh-CN-XiaoxiaoNeural"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 0.0


class TTSResponse(BaseModel):
    """ 语音合成响应 """
    success: bool
    audio_base64: Optional[str] = None
    duration: Optional[float] = None


class VoiceChatRequest(BaseModel):
    """ 语音对话请求 """
    session_id: str
    audio_base64: Optional[str] = None
    text: Optional[str] = None
    mode: Optional[str] = "ptt"


class VoiceChatResponse(BaseModel):
    """ 语音对话响应 """
    success: bool
    text: Optional[str] = None
    response: Optional[str] = None
    audio_base64: Optional[str] = None
    error: Optional[str] = None


class VoiceConfigRequest(BaseModel):
    """ 语音配置更新请求 """
    mode: Optional[str] = None
    stt_provider: Optional[str] = None
    tts_provider: Optional[str] = None
    stt_model: Optional[str] = None
    tts_voice: Optional[str] = None
    language: Optional[str] = None
    auto_tts: Optional[bool] = None


class WakeRequest(BaseModel):
    """ 唤醒词检测请求 """
    audio_base64: str  # Base64 编码的音频
    method: Optional[str] = "energy"


# ==================== 语音识别接口 ====================

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    audio: UploadFile = File(..., description="音频文件"),
    provider: str = Query("openai", description="提供商"),
    model: str = Query("whisper-1", description="模型"),
    language: Optional[str] = Query(None, description="语言代码")
):
    """
    语音识别 (Speech-to-Text)
    支持多种音频格式: mp3, wav, ogg, webm
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="音频数据为空")
        
        # 创建 STT 服务
        stt_config = STTConfig(
            provider=STTProvider(provider),
            model=STTModelSize(model),
            language=language
        )
        stt_service = get_stt_service(stt_config)
        
        # 识别
        result = await stt_service.recognize(audio_data)
        
        logger.info(f"语音识别完成 | 文本长度: {len(result.text)}")
        
        return STTResponse(
            success=True,
            text=result.text,
            language=result.language,
            duration=result.duration
        )
    
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt/base64", response_model=STTResponse)
async def speech_to_text_base64(
    audio_base64: str = Query(..., description="Base64 编码的音频"),
    provider: str = Query("openai", description="提供商"),
    model: str = Query("whisper-1", description="模型"),
    language: Optional[str] = Query(None, description="语言代码")
):
    """
    语音识别 (Base64 音频输入)
    """
    try:
        # 解码音频
        try:
            audio_data = base64.b64decode(audio_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的 Base64 编码")
        
        # 创建 STT 服务
        stt_config = STTConfig(
            provider=STTProvider(provider),
            model=STTModelSize(model),
            language=language
        )
        stt_service = get_stt_service(stt_config)
        
        # 识别
        result = await stt_service.recognize(audio_data)
        
        return STTResponse(
            success=True,
            text=result.text,
            language=result.language,
            duration=result.duration
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 语音合成接口 ====================

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    text: str = Query(..., description="要合成的文本"),
    provider: str = Query("edge", description="提供商"),
    voice: str = Query("zh-CN-XiaoxiaoNeural", description="语音"),
    speed: float = Query(1.0, ge=0.25, le=4.0, description="语速"),
    pitch: float = Query(0.0, ge=-50.0, le=50.0, description="音调")
):
    """
    语音合成 (Text-to-Speech)
    支持 Edge TTS (免费高质量中文) 和 OpenAI TTS API
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="文本不能为空")
        
        # 创建 TTS 服务
        tts_config = TTSConfig(
            provider=TTSProvider(provider),
            voice=TTSVoice(voice),
            speed=speed,
            pitch=pitch
        )
        tts_service = get_tts_service(tts_config)
        
        # 合成
        result = await tts_service.speak(text)
        
        # 编码为 Base64
        audio_base64 = base64.b64encode(result.audio).decode("utf-8")
        
        logger.info(f"语音合成完成 | 文本长度: {len(text)} | 音频大小: {len(result.audio)}")
        
        return TTSResponse(
            success=True,
            audio_base64=audio_base64,
            duration=result.duration
        )
    
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 语音对话接口 ====================

@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(request: VoiceChatRequest):
    """
    语音对话 (STT -> Agent -> TTS)
    完整的语音交互流程
    """
    try:
        session_id = request.session_id
        
        # 获取会话
        session = get_voice_session(session_id)
        
        # 处理音频或文本
        if request.audio_base64:
            audio_data = base64.b64decode(request.audio_base64)
            result = await session.process_audio(audio_data)
        elif request.text:
            # 纯文本输入
            result = await session._call_agent(request.text)
            result = {
                "success": True,
                "text": request.text,
                "response": result,
                "audio": None,
                "error": None
            }
        else:
            raise HTTPException(status_code=400, detail="需要提供 audio_base64 或 text")
        
        # 编码音频为 Base64
        audio_base64 = None
        if result.get("audio"):
            audio_base64 = base64.b64encode(result["audio"]).decode("utf-8")
        
        return VoiceChatResponse(
            success=result["success"],
            text=result.get("text"),
            response=result.get("response"),
            audio_base64=audio_base64,
            error=result.get("error")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 会话管理接口 ====================

@router.get("/status")
async def get_voice_status(
    session_id: str = Query(..., description="会话ID")
):
    """
    获取语音会话状态
    """
    try:
        session = get_voice_session(session_id)
        return session.get_status()
    
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """
    列出所有语音会话
    """
    sessions = list_voice_sessions()
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除语音会话
    """
    try:
        remove_voice_session(session_id)
        return {
            "status": "success",
            "message": f"会话 {session_id} 已删除"
        }
    
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """
    重置语音会话
    """
    try:
        session = get_voice_session(session_id)
        session.reset()
        return {
            "status": "success",
            "message": "会话已重置"
        }
    
    except Exception as e:
        logger.error(f"重置会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 配置接口 ====================

@router.post("/config")
async def update_voice_config(
    config: VoiceConfigRequest,
    session_id: str = Query(..., description="会话ID"),
):
    """
    更新语音配置
    """
    try:
        session = get_voice_session(session_id)
        
        # 更新配置
        if config.mode:
            session.config.mode = VoiceMode(config.mode)
        if config.stt_provider:
            session.config.stt_provider = config.stt_provider
        if config.tts_provider:
            session.config.tts_provider = config.tts_provider
        if config.stt_model:
            session.config.stt_model = config.stt_model
        if config.tts_voice:
            session.config.tts_voice = config.tts_voice
        if config.language:
            session.config.language = config.language
        if config.auto_tts is not None:
            session.config.auto_tts = config.auto_tts
        
        return {
            "status": "success",
            "config": session.config.model_dump()
        }
    
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 唤醒词检测接口 ====================

@router.post("/wake")
async def detect_wake_word(
    request: WakeRequest
):
    """
    唤醒词检测
    检测音频中的唤醒词
    """
    try:
        # 解码音频
        audio_data = base64.b64decode(request.audio_base64)
        
        # 配置
        wake_config = WakeConfig(
            method=WakeMethod(request.method)
        )
        
        # 检测
        detector = get_wake_detector(wake_config)
        result = detector.detect(audio_data)
        
        return {
            "detected": result.detected,
            "wake_word": result.wake_word,
            "confidence": result.confidence,
            "audio_energy": result.audio_energy
        }
    
    except Exception as e:
        logger.error(f"唤醒词检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 模型列表接口 ====================

@router.get("/models")
async def list_voice_models():
    """
    列出可用的语音模型
    """
    return {
        "stt_models": {
            "openai": ["whisper-1"],
            "local": ["tiny", "base", "small", "medium", "large"]
        },
        "tts_providers": {
            "edge": [
                "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunxiNeural",
                "zh-CN-YunjiaoNeural",
                "zh-CN-ShaolingNeural",
                "en-US-JennyNeural",
                "en-US-GuyNeural"
            ],
            "openai": ["tts-1", "tts-1-hd"],
            "elevenlabs": [
                "rachel", "clarke", "domi"
            ]
        }
    }