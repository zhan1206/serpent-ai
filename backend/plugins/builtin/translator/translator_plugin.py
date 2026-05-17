# -*- coding: utf-8 -*-
"""
翻译插件 - 多语言翻译
优先使用 LibreTranslate，回退到 MyMemory 免费API
"""

import json
import logging
import urllib.parse
import urllib.request
from typing import Dict, List, Any, Optional

from backend.plugins.plugin_base import ToolPlugin
from backend.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

UA = "SerpentAI/1.0 (Plugin; Translator)"

# 语言代码映射（常用语言）
LANG_MAP = {
    "中文": "zh", " chinese": "zh", "zh": "zh", "zh-cn": "zh", "zh-tw": "zh-TW",
    "英语": "en", " english": "en", "en": "en",
    "日语": "ja", " japanese": "ja", "ja": "ja",
    "韩语": "ko", " korean": "ko", "ko": "ko",
    "法语": "fr", " french": "fr", "fr": "fr",
    "德语": "de", " german": "de", "de": "de",
    "西班牙语": "es", " spanish": "es", "es": "es",
    "俄语": "ru", " russian": "ru", "ru": "ru",
    "葡萄牙语": "pt", " portuguese": "pt", "pt": "pt",
    "意大利语": "it", " italian": "it", "it": "it",
    "阿拉伯语": "ar", " arabic": "ar", "ar": "ar",
}


def _resolve_lang(lang: str) -> str:
    """解析语言代码"""
    lang_lower = lang.lower().strip()
    if lang_lower in LANG_MAP:
        mapped = LANG_MAP[lang_lower]
        return mapped if isinstance(mapped, str) else mapped
    return lang_lower


def _translate_mymemory(text: str, source: str, target: str) -> Optional[str]:
    """
    使用 MyMemory API 翻译（免费，无需API密钥）
    """
    try:
        params = urllib.parse.urlencode({
            "q": text[:500],  # 限制长度
            "langpair": f"{source}|{target}",
        })
        url = f"https://api.mymemory.translated.net/get?{params}"
        
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("responseStatus") == 200:
            translated = data["responseData"]["translatedText"]
            # MyMemory 有时会返回大写的结果
            if translated.isupper() and not text.isupper():
                translated = translated.capitalize()
            return translated
        return None
    except Exception as e:
        logger.error(f"MyMemory 翻译失败: {e}")
        return None


def _translate_libre(text: str, source: str, target: str,
                     api_url: str = "https://libretranslate.com/translate") -> Optional[str]:
    """
    使用 LibreTranslate 翻译
    """
    try:
        payload = json.dumps({
            "q": text,
            "source": source,
            "target": target,
            "format": "text",
        }).encode("utf-8")
        
        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        return data.get("translatedText")
    except Exception as e:
        logger.debug(f"LibreTranslate 翻译失败: {e}")
        return None


class TranslatorPlugin(ToolPlugin):
    """翻译插件"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "translate",
                "description": "多语言翻译工具。支持中文、英语、日语、韩语、法语、德语、西班牙语等语言互译。自动检测源语言（可手动指定）。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要翻译的文本"
                        },
                        "target_lang": {
                            "type": "string",
                            "description": "目标语言，如 'en'（英语）, 'zh'（中文）, 'ja'（日语）"
                        },
                        "source_lang": {
                            "type": "string",
                            "description": "源语言（可选，不提供则自动检测）。如 'zh', 'en'"
                        }
                    },
                    "required": ["text", "target_lang"]
                },
                "handler": self._handle_translate,
                "category": "translation"
            },
        ]
    
    def _handle_translate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        text = arguments["text"]
        target_lang = _resolve_lang(arguments["target_lang"])
        source_lang = _resolve_lang(arguments.get("source_lang", "auto"))
        
        if source_lang == target_lang:
            return {
                "original": text,
                "translated": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "message": "源语言和目标语言相同",
            }
        
        # 尝试 LibreTranslate
        result = _translate_libre(text, source_lang, target_lang)
        engine = "LibreTranslate"
        
        # 回退到 MyMemory
        if not result:
            src = "autodetect" if source_lang == "auto" else source_lang
            result = _translate_mymemory(text, src, target_lang)
            engine = "MyMemory"
        
        if not result:
            return {
                "error": "翻译失败，所有翻译服务均不可用",
                "original": text,
            }
        
        return {
            "original": text,
            "translated": result,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "engine": engine,
        }


def create_plugin(manifest: PluginManifest) -> TranslatorPlugin:
    return TranslatorPlugin(manifest)
