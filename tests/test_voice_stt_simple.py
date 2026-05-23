"""
Simple tests for SpeechToText module - improve coverage from 0%
Focuses on initialization, config, and basic methods
"""
import pytest
from backend.voice.speech_to_text import (
    SpeechToText, STTConfig, STTResult, 
    STTProvider, STTModelSize
)


class TestSpeechToTextBasics:
    """Basic tests for SpeechToText module"""
    
    def test_stt_config_defaults(self):
        """Test STTConfig with defaults"""
        config = STTConfig()
        assert config.provider == STTProvider.OPENAI
        assert config.model == STTModelSize.WHISPER_1
        assert config.language is None
        assert config.temperature == 0.0
        assert config.response_format == "json"
        assert config.api_key is None
        assert config.api_base == "https://api.openai.com/v1"
    
    def test_stt_config_custom(self):
        """Test STTConfig with custom values"""
        config = STTConfig(
            provider=STTProvider.LOCAL,
            model=STTModelSize.BASE,
            language="zh",
            temperature=0.5,
            response_format="verbose_json"
        )
        assert config.provider == STTProvider.LOCAL
        assert config.model == STTModelSize.BASE
        assert config.language == "zh"
        assert config.temperature == 0.5
        assert config.response_format == "verbose_json"
    
    def test_stt_result(self):
        """Test STTResult dataclass"""
        result = STTResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.language is None
        assert result.duration is None
        assert result.confidence is None
        assert result.words is None
        
        # With all fields
        result2 = STTResult(
            text="Hello",
            language="en",
            duration=5.5,
            confidence=0.95,
            words=[{"word": "Hello"}]
        )
        assert result2.language == "en"
        assert result2.duration == 5.5
    
    def test_speech_to_text_init(self):
        """Test SpeechToText initialization"""
        stt = SpeechToText()
        assert stt.config is not None
        assert stt.config.provider == STTProvider.OPENAI
        assert stt._session is None
        
        # With custom config
        config = STTConfig(provider=STTProvider.LOCAL)
        stt2 = SpeechToText(config=config)
        assert stt2.config.provider == STTProvider.LOCAL
    
    def test_stt_provider_enum(self):
        """Test STTProvider enum"""
        assert STTProvider.OPENAI == "openai"
        assert STTProvider.LOCAL == "local"
        assert STTProvider.FAL == "fal"
    
    def test_stt_model_size_enum(self):
        """Test STTModelSize enum"""
        assert STTModelSize.TINY == "tiny"
        assert STTModelSize.BASE == "base"
        assert STTModelSize.SMALL == "small"
        assert STTModelSize.MEDIUM == "medium"
        assert STTModelSize.LARGE == "large"
        assert STTModelSize.WHISPER_1 == "whisper-1"
