"""
SerpentAI 语音路由
FastAPI 路由 - 语音识别、语音合成、语音会话管理
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import tempfile
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# 全局语音会话管理器
_voice_session_manager = None


def get_voice_session_manager():
    global _voice_session_manager
    if _voice_session_manager is None:
        from backend.voice.voice_session import VoiceSessionManager
        _voice_session_manager = VoiceSessionManager()
    return _voice_session_manager


# ==================== 请求/响应模型 ====================

class STTRequest(BaseModel):
    """语音转文字请求"""
    language: str = "zh-CN"
    model: str = "whisper-1"
    prompt: str = ""


class TTSRequest(BaseModel):
    """文字转语音请求"""
    text: str
    voice: str = "alloy"
    speed: float = 1.0
    format: str = "mp3"


class VoiceChatRequest(BaseModel):
    """语音聊天请求"""
    audio_data: str  # Base64编码的音频
    language: str = "zh-CN"
    session_id: str = ""


# ==================== 语音转文字 ====================

@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("zh-CN"),
    model: str = Form("whisper-1")
):
    """
    语音转文字
    上传音频文件，返回识别文本
    支持格式: mp3, wav, ogg, webm, m4a
    """
    try:
        # 保存上传的音频
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # 调用 STT 服务
            from backend.voice.speech_to_text import transcribe_audio
            
            result = await transcribe_audio(
                audio_path=tmp_path,
                language=language,
                model=model
            )
            
            return {
                "text": result.get("text", ""),
                "language": language,
                "duration": result.get("duration", 0),
                "model": model
            }
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"语音转文字失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt/stream")
async def speech_to_text_stream(
    audio: UploadFile = File(...),
    language: str = Form("zh-CN")
):
    """
    流式语音转文字（用于麦克风实时输入）
    """
    try:
        # 读取音频数据
        audio_data = await audio.read()
        
        from backend.voice.speech_to_text import transcribe_audio_stream
        
        # 流式处理
        async def generate():
            result = await transcribe_audio_stream(audio_data, language)
            yield f"data: {result}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    
    except Exception as e:
        logger.error(f"流式语音转文字失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 文字转语音 ====================

@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    文字转语音
    使用 Edge TTS (免费，高质量，中文支持好)
    或 OpenAI TTS API
    """
    try:
        from backend.voice.text_to_speech import synthesize_speech
        
        # 生成语音
        audio_data = await synthesize_speech(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            format=request.format
        )
        
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=output.mp3"}
        )
    
    except Exception as e:
        logger.error(f"文字转语音失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/voices")
async def list_tts_voices():
    """
    列出可用的 TTS 声音
    """
    try:
        from backend.voice.text_to_speech import get_available_voices
        
        voices = get_available_voices()
        
        return {
            "voices": voices,
            "count": len(voices)
        }
    
    except Exception as e:
        logger.error(f"获取TTS声音列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 语音聊天 ====================

@router.post("/chat")
async def voice_chat(request: VoiceChatRequest):
    """
    语音聊天
    接收音频 -> STT -> AI处理 -> TTS -> 返回音频
    """
    try:
        from backend.voice.voice_session import VoiceSessionManager
        
        manager = get_voice_session_manager()
        session = manager.get_or_create_session(request.session_id)
        
        # 解码音频
        import base64
        audio_bytes = base64.b64decode(request.audio_data)
        
        # STT
        from backend.voice.speech_to_text import transcribe_audio
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            stt_result = await transcribe_audio(tmp_path, language=request.language)
            text = stt_result.get("text", "")
        finally:
            os.unlink(tmp_path)
        
        if not text:
            return {"error": "未能识别语音"}
        
        # 调用 AI
        from routes.agent import chat_with_agent
        
        chat_result = await chat_with_agent(
            message=text,
            session_id=session.id
        )
        
        response_text = chat_result.get("response", "")
        
        # TTS
        from backend.voice.text_to_speech import synthesize_speech
        
        audio_data = await synthesize_speech(
            text=response_text,
            voice="zh-CN-XiaoxiaoNeural"  # 中文语音
        )
        
        # 返回 base64 编码的音频
        audio_b64 = base64.b64encode(audio_data).decode()
        
        return {
            "text": text,
            "response": response_text,
            "audio": audio_b64,
            "session_id": session.id
        }
    
    except Exception as e:
        logger.error(f"语音聊天失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 语音会话管理 ====================

@router.get("/session/{session_id}")
async def get_voice_session(session_id: str):
    """获取语音会话"""
    manager = get_voice_session_manager()
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return session.to_dict()


@router.get("/sessions")
async def list_voice_sessions():
    """列出所有语音会话"""
    manager = get_voice_session_manager()
    sessions = manager.list_sessions()
    
    return {
        "sessions": [s.to_dict() for s in sessions],
        "count": len(sessions)
    }


@router.delete("/session/{session_id}")
async def delete_voice_session(session_id: str):
    """删除语音会话"""
    manager = get_voice_session_manager()
    manager.delete_session(session_id)
    
    return {"deleted": True, "session_id": session_id}


# ==================== 唤醒词 ====================

@router.post("/wake")
async def wake_word_detection(
    audio: UploadFile = File(...),
    threshold: float = Form(0.5)
):
    """
    唤醒词检测
    检测音频中是否包含唤醒词
    """
    try:
        audio_data = await audio.read()
        
        from backend.voice.wake_word import detect_wake_word
        
        result = await detect_wake_word(audio_data, threshold=threshold)
        
        return {
            "detected": result.get("detected", False),
            "wake_word": result.get("wake_word", None),
            "confidence": result.get("confidence", 0),
            "threshold": threshold
        }
    
    except Exception as e:
        logger.error(f"唤醒词检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wake/words")
async def list_wake_words():
    """列出可用的唤醒词"""
    from backend.voice.wake_word import get_available_wake_words
    
    wake_words = get_available_wake_words()
    
    return {
        "wake_words": wake_words,
        "count": len(wake_words)
    }


# ==================== 状态 ====================

@router.get("/status")
async def get_voice_status():
    """获取语音服务状态"""
    manager = get_voice_session_manager()
    
    return {
        "status": "ready",
        "active_sessions": len(manager.list_sessions()),
        "stt_available": True,
        "tts_available": True,
        "wake_word_available": True
    }
