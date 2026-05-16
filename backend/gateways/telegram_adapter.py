"""
Telegram平台适配器
支持Telegram消息、回调、事件处理
"""
from typing import Dict, Any, Optional, Callable, Awaitable
import logging
from core.logging_config import get_logger
from . import PlatformAdapter, Message, Response

logger = get_logger(__name__)


class TelegramAdapter(PlatformAdapter):
    """Telegram平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.use_webhook = config.get("use_webhook", False)
        self.webhook_url = config.get("webhook_url", "")
    
    def get_platform_name(self) -> str:
        return "telegram"
    
    async def initialize(self) -> bool:
        """初始化Telegram连接"""
        try:
            self.bot_info = {
                "bot_token": self.bot_token[:10] + "..." if self.bot_token else "",
                "platform": "telegram",
                "connected": True
            }
            self.logger.info(f"Telegram适配器初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"Telegram适配器初始化失败: {e}")
            return False
    
    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到Telegram"""
        try:
            if not response.content:
                self.logger.warning("响应内容为空")
                return False
            # TODO: 实现 Telegram 消息发送 API
            self.logger.info(f"发送消息到Telegram: {target}")
            return True
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信到Telegram"""
        try:
            if not user_id:
                self.logger.warning("用户ID为空")
                return False
            if not response.content:
                self.logger.warning("响应内容为空")
                return False
            # TODO: 实现 Telegram 私信 API
            self.logger.info(f"发送私信到用户: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"发送私信失败: {e}")
            return False
    
    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """处理Telegram消息"""
        try:
            if not handler:
                self.logger.warning("消息处理器未设置")
                return
            # TODO: 实现 Telegram 消息监听
            self.logger.debug(f"消息处理器已注册: {message}")
        except Exception as e:
            self.logger.error(f"注册消息处理器失败: {e}")
    
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """处理Telegram回调"""
        try:
            if not callback_id:
                self.logger.warning("回调ID为空")
                return
            # TODO: 实现 Telegram 回调处理
            self.logger.debug(f"回调处理器已注册: {callback_id}")
        except Exception as e:
            self.logger.error(f"注册回调处理器失败: {e}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            self.logger.info("清理Telegram适配器资源")
        except Exception:
            pass