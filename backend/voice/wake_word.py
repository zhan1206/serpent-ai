"""
SerpentAI Wake Word Detection 模块
使用简单能量检测或关键词识别进行唤醒词检测
支持中文唤醒词："小蛇"、"Serpent"
"""
import logging
from typing import Optional, List, Callable, AsyncGenerator
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field

from core.logging_config import get_logger

logger = get_logger(__name__)


class WakeMethod(str, Enum):
    """ 唤醒方法 """
    ENERGY = "energy"       # 能量检测（简单）
    KEYWORD = "keyword"     # 关键词识别（需要模型）
    VAD = "vad"            # 语音活动检测


class WakeConfig(BaseModel):
    """ 唤醒配置 """
    method: WakeMethod = WakeMethod.ENERGY
    wake_words: List[str] = Field(
        default_factory=lambda: ["小蛇", "Serpent", "小蛇助教"],
        description="唤醒词列表"
    )
    energy_threshold: float = Field(
        0.02,
        ge=0.001,
        le=0.5,
        description="能量阈值"
    )
    min_duration: float = Field(
        0.3,
        ge=0.1,
        le=2.0,
        description="最小唤醒时长（秒）"
    )
    sample_rate: int = Field(
        16000,
        description="采样率"
    )


class WakeResult(BaseModel):
    """ 唤醒结果 """
    detected: bool
    wake_word: Optional[str] = None
    confidence: float = 0.0
    audio_energy: float = 0.0


class WakeWordDetector:
    """
    唤醒词检测器
    使用简单能量检测或关键词 spotting
    """
    
    def __init__(self, config: Optional[WakeConfig] = None):
        self.config = config or WakeConfig()
        self._energy_history: List[float] = []
        self._is_listening = False
    
    def detect(
        self,
        audio_data: bytes,
        sample_rate: Optional[int] = None
    ) -> WakeResult:
        """
        检测唤醒词
        
        Args:
            audio_data: 原始音频数据（16位 PCM）
            sample_rate: 采样率
        
        Returns:
            WakeResult: 检测结果
        """
        config = self.config
        sample_rate = sample_rate or config.sample_rate
        
        # 计算音频能量
        audio_np = self._parse_audio(audio_data, sample_rate)
        energy = self._calculate_energy(audio_np)
        
        self._energy_history.append(energy)
        if len(self._energy_history) > 100:
            self._energy_history.pop(0)
        
        # 能量检测模式
        if config.method == WakeMethod.ENERGY:
            return self._detect_energy(energy)
        
        # 简单关键词检测（基于能量模式）
        elif config.method == WakeMethod.KEYWORD:
            return self._detect_keyword(audio_np, energy)
        
        # VAD 模式
        elif config.method == WakeMethod.VAD:
            return self._detect_vad(energy)
        
        return WakeResult(detected=False, audio_energy=energy)
    
    def _parse_audio(self, audio_data: bytes, sample_rate: int) -> np.ndarray:
        """解析 PCM 音频数据"""
        # 假设 16 位有符号整数
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        
        # 归一化到 -1.0 ~ 1.0
        audio_np = audio_np.astype(np.float32) / 32768.0
        
        return audio_np
    
    def _calculate_energy(self, audio_np: np.ndarray) -> float:
        """计算音频能量（RMS）"""
        return float(np.sqrt(np.mean(audio_np ** 2)))
    
    def _detect_energy(self, energy: float) -> WakeResult:
        """基于能量检测"""
        config = self.config
        
        # 简单阈值检测
        detected = energy > config.energy_threshold
        
        if detected:
            logger.info(f"唤醒词检测成功 | 能量: {energy:.4f} | 阈值: {config.energy_threshold}")
            return WakeResult(
                detected=True,
                confidence=min(energy / config.energy_threshold, 1.0),
                audio_energy=energy
            )
        
        return WakeResult(detected=False, audio_energy=energy)
    
    def _detect_keyword(
        self,
        audio_np: np.ndarray,
        energy: float
    ) -> WakeResult:
        """
        关键词检测
        使用简化的梅尔频率倒谱系数（MFCC）特征
        注意：完整实现需要训练好的唤醒词模型
        """
        config = self.config
        
        # 计算过零率（简单的语音检测特征）
        zero_crossing = np.sum(np.abs(np.diff(np.sign(audio_np)))) / len(audio_np)
        
        # 简单的语音/非语音判断
        is_speech = energy > config.energy_threshold and zero_crossing > 0.1
        
        # 如果检测到语音活动，记录状态
        if is_speech and not self._is_listening:
            logger.info("开始监听语音输入...")
            self._is_listening = True
        
        # 这里可以添加更复杂的唤醒词识别逻辑
        # 当前返回 VAD 结果
        if is_speech:
            return WakeResult(
                detected=False,
                confidence=min(energy / config.energy_threshold, 1.0),
                audio_energy=energy
            )
        
        # 语音结束
        if self._is_listening:
            logger.info("语音输入结束")
            self._is_listening = False
        
        return WakeResult(detected=False, audio_energy=energy)
    
    def _detect_vad(self, energy: float) -> WakeResult:
        """语音活动检测"""
        config = self.config
        
        detected = energy > config.energy_threshold
        
        if detected:
            return WakeResult(
                detected=detected,
                confidence=min(energy / config.energy_threshold, 1.0),
                audio_energy=energy
            )
        
        return WakeResult(detected=False, audio_energy=energy)
    
    async def detect_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        on_wake: Optional[Callable[[WakeResult], None]] = None
    ) -> AsyncGenerator[WakeResult, None]:
        """
        流式唤醒词检测
        
        Args:
            audio_stream: 音频流
            on_wake: 唤醒回调
        
        Yields:
            WakeResult: 检测结果
        """
        config = self.config
        buffer = b""
        
        async for chunk in audio_stream:
            buffer += chunk
            
            # 每 16000 字节（约 0.5 秒 @ 16kHz）处理一次
            if len(buffer) >= config.sample_rate * 2:  # 1 秒音频
                result = self.detect(buffer)
                yield result
                
                if result.detected and on_wake:
                    on_wake(result)
                
                buffer = b""
        
        # 处理剩余数据
        if buffer:
            result = self.detect(buffer)
            yield result
    
    async def listen_for_wake(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        timeout: float = 30.0
    ) -> Optional[WakeResult]:
        """
        等待唤醒
        
        Args:
            audio_stream: 音频流
            timeout: 超时时间（秒）
        
        Returns:
            WakeResult: 唤醒结果，None 表示超时
        """
        import asyncio
        
        config = self.config
        timeout_samples = int(config.sample_rate * timeout)
        samples_received = 0
        
        buffer = b""
        
        try:
            async for chunk in audio_stream:
                buffer += chunk
                samples_received += len(chunk)
                
                if samples_received >= config.sample_rate * 2:  # 至少 1 秒
                    result = self.detect(buffer)
                    
                    if result.detected:
                        return result
                    
                    samples_received = 0
                    buffer = b""
            
            return None
        
        except asyncio.TimeoutError:
            logger.warning(f"等待唤醒超时: {timeout}秒")
            return None


# 全局唤醒词检测器
_wake_detector: Optional[WakeWordDetector] = None


def get_wake_detector(config: Optional[WakeConfig] = None) -> WakeWordDetector:
    """获取全局唤醒词检测器"""
    global _wake_detector
    if _wake_detector is None:
        _wake_detector = WakeWordDetector(config)
    return _wake_detector