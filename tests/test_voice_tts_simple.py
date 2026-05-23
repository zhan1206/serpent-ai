"""
Simple tests for TextToSpeech module - improve coverage from 0%
Focuses on initialization, config, and basic methods
"""
import pytest
from backend.voice.text_to_speech import (
    TextToSpeech, TTSConfig, TTSResult,
    TTSProvider, TTSVoice
)


class TestTextToSpeechBasics:
    """Basic tests for TextToSpeech module"""
    
    def test_tts_config_defaults(self):
        """Test TTSConfig with defaults"""
        config = TTSConfig()
        assert config.provider == TTSProvider.EDGE
        assert config.voice == TTSVoice.ZH_CN_XIAOXIAO
        assert config.language is None
        assert config.speed == 1.0
        assert config.pitch == 0.0
        assert config.volume == 1.0
        assert config.api_key is None
        assert config.api_base == "https://api.openai.com/v1"
    
    def test_tts_config_custom(self):
        """Test TTSConfig with custom values"""
        config = TTSConfig(
            provider=TTSProvider.OPENAI,
            voice=TTSVoice.OPENAI_TTS_1,
            speed=1.5,
            pitch=10.0,
        )
        assert config.provider == TTSProvider.OPENAI
        assert config.voice == TTSVoice.OPENAI_TTS_1
        assert config.speed == 1.5
        assert config.pitch == 10.0
    
    def test_tts_result(self):
        """Test TTSResult dataclass"""
        result = TTSResult(audio=b"test audio")
        assert result.audio == b"test audio"
        assert result.audio_base64 is None
        assert result.format == "mp3"
        assert result.duration is None
        
        # With all fields
        result2 = TTSResult(
            audio=b"data",
            audio_base64="base64data",
            format="wav",
            duration=5.5
        )
        assert result2.format == "wav"
        assert result2.duration == 5.5
    
    def test_text_to_speech_init(self):
        """Test TextToSpeech initialization"""
        tts = TextToSpeech()
        assert tts.config is not None
        assert tts.config.provider == TTSProvider.EDGE
        assert tts._session is None
        
        # With custom config
        config = TTSConfig(provider=TTSProvider.OPENAI)
        tts2 = TextToSpeech(config=config)
        assert tts2.config.provider == TTSProvider.OPENAI
    
    def test_tts_provider_enum(self):
        """Test TTSProvider enum"""
        assert TTSProvider.EDGE == "edge"
        assert TTSProvider.OPENAI == "openai"
        assert TTSProvider.ELEVENLABS == "elevenlabs"
    
    def test_tts_voice_enum(self):
        """Test TTSVoice enum"""
        assert TTSVoice.ZH_CN_XIAOXIAO == "zh-CN-XiaoxiaoNeural"
        assert TTSVoice.ZH_CN_YUNQI == "zh-CN-YunxiNeural"
        assert TTSVoice.EN_US_JENNY == "en-US-JennyNeural"
        assert TTSVoice.OPENAI_TTS_1 == "tts-1"
        assert TTSVoice.ELEVENLABS_RACHEL == "rachel"
    
    def test_tts_config_speed_clamping(self):
        """Test TTSConfig speed bounds"""
        config = TTSConfig(speed=0.25)
        assert config.speed == 0.25
        
        config2 = TTSConfig(speed=4.0)
        assert config2.speed == 4.0
    
    def test_tts_config_pitch_range(self):
        """Test TTSConfig pitch range"""
        config = TTSConfig(pitch=-50.0)
        assert config.pitch == -50.0
        
        config2 = TTSConfig(pitch=50.0)
        assert config2.pitch == 50.0
    
    def test_tts_config_volume_range(self):
        """Test TTSConfig volume range"""
        config = TTSConfig(volume=0.0)
        assert config.volume == 0.0
        
        config2 = TTSConfig(volume=2.0)
        assert config2.volume == 2.0
