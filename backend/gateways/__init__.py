"""
SerpentAI 多通道网关层
集成各种IM平台：飞书、Discord、Telegram、Slack、微信、QQ等
支持消息、回调、事件处理
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
import logging
from core.logging_config import get_logger

logger = get_logger(__name__)


# ==================== 消息类型定义 ====================

class Message:
    """统一消息格式"""
    def __init__(
        self,
        msg_id: str,
        platform: str,
        msg_type: str,
        content: str,
        sender: Dict[str, Any],
        room: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.msg_id = msg_id
        self.platform = platform
        self.msg_type = msg_type
        self.content = content
        self.sender = sender
        self.room = room
        self.raw_data = raw_data or {}
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "platform": self.platform,
            "msg_type": self.msg_type,
            "content": self.content,
            "sender": self.sender,
            "room": self.room,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class Response:
    """统一响应格式"""
    def __init__(
        self,
        message: str,
        msg_type: str = "text",
        markdown: Optional[str] = None,
        attachments: Optional[list] = None,
        keyboard: Optional[list] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.msg_type = msg_type
        self.markdown = markdown
        self.attachments = attachments or []
        self.keyboard = keyboard
        self.meta = meta or {}


# ==================== 平台适配器基类 ====================

class PlatformAdapter(ABC):
    """平台适配器抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.get_platform_name()
        self.enabled = config.get("enabled", False)
        self.bot_info: Dict[str, Any] = {}
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """获取平台名称"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化平台连接"""
        pass
    
    @abstractmethod
    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信"""
        pass
    
    @abstractmethod
    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """处理收到的消息"""
        pass
    
    @abstractmethod
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """处理回调"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "platform": self.platform_name,
            "enabled": self.enabled,
            "connected": self.enabled,
            "bot_info": self.bot_info
        }


# ==================== 网关管理器 ====================

class GatewayManager:
    """多通道网关管理器"""
    
    _instance: Optional["GatewayManager"] = None
    
    def __init__(self):
        self.adapters: Dict[str, PlatformAdapter] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.callback_handlers: Dict[str, Callable] = {}
        self.logger = logger
    
    @classmethod
    def get_instance(cls) -> "GatewayManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """初始化所有平台适配器"""
        results = {}
        
        for platform_name, config in configs.items():
            if not config.get("enabled", False):
                self.logger.info(f"跳过未启用的平台: {platform_name}")
                continue
            
            try:
                adapter = self._create_adapter(platform_name, config)
                if adapter:
                    success = await adapter.initialize()
                    if success:
                        self.adapters[platform_name] = adapter
                        results[platform_name] = {"status": "success", "bot_info": adapter.bot_info}
                        self.logger.info(f"平台 {platform_name} 初始化成功")
                    else:
                        results[platform_name] = {"status": "failed", "error": "初始化失败"}
                        self.logger.error(f"平台 {platform_name} 初始化失败")
            except Exception as e:
                results[platform_name] = {"status": "error", "error": str(e)}
                self.logger.error(f"平台 {platform_name} 初始化异常: {e}")
        
        return results
    
    def _create_adapter(self, platform_name: str, config: Dict[str, Any]) -> Optional[PlatformAdapter]:
        """创建平台适配器"""
        if platform_name == "feishu":
            from .feishu_adapter import FeishuAdapter
            return FeishuAdapter(config)
        elif platform_name == "discord":
            from .discord_adapter import DiscordAdapter
            return DiscordAdapter(config)
        elif platform_name == "telegram":
            from .telegram_adapter import TelegramAdapter
            return TelegramAdapter(config)
        elif platform_name == "slack":
            from .slack_adapter import SlackAdapter
            return SlackAdapter(config)
        elif platform_name == "wechat":
            from .wechat_adapter import WechatAdapter
            return WechatAdapter(config)
        elif platform_name == "qq":
            from .qq_adapter import QQAdapter
            return QQAdapter(config)
        elif platform_name == "dingtalk":
            from .dingtalk_adapter import DingtalkAdapter
            return DingtalkAdapter(config)
        elif platform_name == "whatsapp":
            from .whatsapp_adapter import WhatsAppAdapter
            return WhatsAppAdapter(config)
        elif platform_name == "signal":
            from .signal_adapter import SignalAdapter
            return SignalAdapter(config)
        elif platform_name == "line":
            from .line_adapter import LINEAdapter
            return LINEAdapter(config)
        elif platform_name == "email":
            from .email_adapter import EmailAdapter
            return EmailAdapter(config)
        elif platform_name == "webhook":
            from .webhook_adapter import WebhookAdapter
            return WebhookAdapter(config)
        else:
            self.logger.warning(f"不支持的平台: {platform_name}")
            return None
    
    async def send_message(self, platform: str, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到指定平台"""
        if platform not in self.adapters:
            self.logger.error(f"平台未初始化: {platform}")
            return False
        
        try:
            return await self.adapters[platform].send_message(response, target)
        except Exception as e:
            self.logger.error(f"发送消息失败 [{platform}]: {e}")
            return False
    
    async def send_direct_message(self, platform: str, user_id: str, response: Response) -> bool:
        """发送私信到指定平台"""
        if platform not in self.adapters:
            self.logger.error(f"平台未初始化: {platform}")
            return False
        
        try:
            return await self.adapters[platform].send_direct_message(user_id, response)
        except Exception as e:
            self.logger.error(f"发送私信失败 [{platform}]: {e}")
            return False
    
    async def broadcast(self, platforms: list, response: Response, targets: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """广播消息到多个平台"""
        results = {}
        
        for platform in platforms:
            target = targets.get(platform) if targets else None
            results[platform] = await self.send_message(platform, response, target or {})
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查所有平台"""
        results = {"total": len(self.adapters), "adapters": {}}
        
        for platform, adapter in self.adapters.items():
            try:
                results["adapters"][platform] = await adapter.health_check()
            except Exception as e:
                results["adapters"][platform] = {
                    "platform": platform,
                    "enabled": True,
                    "connected": False,
                    "error": str(e)
                }
        
        results["connected_count"] = sum(1 for a in results["adapters"].values() if a.get("connected"))
        return results
    
    async def cleanup(self) -> None:
        """清理所有适配器"""
        for adapter in self.adapters.values():
            try:
                await adapter.cleanup()
            except Exception as e:
                self.logger.error(f"清理适配器失败: {e}")
        
        self.adapters.clear()


# ==================== 消息路由器 ====================

class MessageRouter:
    """消息路由器 - 根据平台分发消息"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable[[Message], Awaitable[Response]]] = {}
        self.fallback_handler: Optional[Callable[[Message], Awaitable[Response]]] = None
    
    def register_handler(self, platform: str, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """注册消息处理器"""
        self.handlers[platform] = handler
    
    def set_fallback_handler(self, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """设置默认处理器"""
        self.fallback_handler = handler
    
    async def route(self, message: Message) -> Optional[Response]:
        """路由消息到对应处理器"""
        handler = self.handlers.get(message.platform, self.fallback_handler)
        
        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.error(f"消息处理异常 [{message.platform}]: {e}")
                return Response(message="处理消息时发生错误")
        
        return None


# ==================== 回调处理器 ====================

class CallbackHandler:
    """回调处理器"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def register(self, callback_id: str, handler: Callable) -> None:
        """注册回调处理器"""
        self.handlers[callback_id] = handler
    
    async def handle(self, callback_id: str, data: Dict[str, Any]) -> Optional[Response]:
        """处理回调"""
        if callback_id in self.handlers:
            try:
                return await self.handlers[callback_id](data)
            except Exception as e:
                logger.error(f"回调处理异常 [{callback_id}]: {e}")
                return Response(message="处理回调时发生错误")
        
        return None


# ==================== 全局实例 ====================

_gateway_manager: Optional[GatewayManager] = None
_message_router: Optional[MessageRouter] = None
_callback_handler: Optional[CallbackHandler] = None


def get_gateway_manager() -> GatewayManager:
    global _gateway_manager
    if _gateway_manager is None:
        _gateway_manager = GatewayManager.get_instance()
    return _gateway_manager


def get_message_router() -> MessageRouter:
    global _message_router
    if _message_router is None:
        _message_router = MessageRouter()
    return _message_router


def get_callback_handler() -> CallbackHandler:
    global _callback_handler
    if _callback_handler is None:
        _callback_handler = CallbackHandler()
    return _callback_handler