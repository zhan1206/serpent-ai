"""
Telegram平台适配器
支持Telegram消息、回调、事件处理
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List
import aiohttp
import logging
import json
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
        self.session: Optional[aiohttp.ClientSession] = None
        self.message_handler: Optional[Callable] = None
        self.callback_handlers: Dict[str, Callable] = {}
    
    def get_platform_name(self) -> str:
        return "telegram"
    
    async def _make_request(self, method: str, **params) -> Optional[Dict[str, Any]]:
        """发送Telegram API请求"""
        try:
            url = f"{self.api_url}/{method}"
            async with self.session.post(url, json=params) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                else:
                    self.logger.error(f"Telegram API错误: {data}")
                    return None
        except Exception as e:
            self.logger.error(f"API请求失败: {e}")
            return None
    
    async def initialize(self) -> bool:
        """初始化Telegram连接"""
        try:
            self.session = aiohttp.ClientSession()
            
            # 获取Bot信息验证token
            bot_info = await self._make_request("getMe")
            if bot_info:
                self.bot_info = {
                    "bot_id": bot_info.get("id"),
                    "username": bot_info.get("username"),
                    "first_name": bot_info.get("first_name"),
                    "supports_inline_queries": bot_info.get("supports_inline_queries", False),
                    "platform": "telegram",
                    "connected": True
                }
                self.logger.info(f"Telegram Bot {bot_info.get('username')} 登录成功")
                return True
            else:
                self.logger.error("Telegram Bot Token验证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"Telegram适配器初始化失败: {e}")
            return False
    
    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到Telegram"""
        try:
            if not response.content:
                self.logger.warning("响应内容为空")
                return False
            
            chat_id = target.get("chat_id")
            if not chat_id:
                self.logger.warning("chat_id未指定")
                return False
            
            # 构建发送参数
            params = {
                "chat_id": chat_id,
                "text": response.content,
                "parse_mode": response.metadata.get("parse_mode", "Markdown")
            }
            
            # 添加reply_markup如果存在
            if response.metadata.get("reply_markup"):
                params["reply_markup"] = response.metadata["reply_markup"]
            
            result = await self._make_request("sendMessage", **params)
            if result:
                self.logger.info(f"消息发送成功: {result.get('message_id')}")
                return True
            return False
                    
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信到Telegram用户"""
        return await self.send_message(response, {"chat_id": user_id})
    
    async def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> bool:
        """发送图片"""
        try:
            params = {
                "chat_id": chat_id,
                "photo": photo_url
            }
            if caption:
                params["caption"] = caption
            
            result = await self._make_request("sendPhoto", **params)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"发送图片失败: {e}")
            return False
    
    async def send_document(self, chat_id: str, document: str, caption: str = "") -> bool:
        """发送文件"""
        try:
            params = {
                "chat_id": chat_id,
                "document": document
            }
            if caption:
                params["caption"] = caption
            
            result = await self._make_request("sendDocument", **params)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"发送文件失败: {e}")
            return False
    
    async def send_inline_keyboard(self, chat_id: str, text: str, keyboard: List[List[Dict]]) -> bool:
        """发送带内联键盘的消息"""
        try:
            reply_markup = {"inline_keyboard": keyboard}
            params = {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup
            }
            
            result = await self._make_request("sendMessage", **params)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"发送键盘失败: {e}")
            return False
    
    async def edit_message_text(self, chat_id: str, message_id: int, text: str, keyboard: Dict = None) -> bool:
        """编辑消息文本"""
        try:
            params = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text
            }
            if keyboard:
                params["reply_markup"] = keyboard
            
            result = await self._make_request("editMessageText", **params)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"编辑消息失败: {e}")
            return False
    
    async def answer_callback_query(self, callback_id: str, text: str = "", show_alert: bool = False) -> bool:
        """回复callback_query"""
        try:
            params = {
                "callback_query_id": callback_id
            }
            if text:
                params["text"] = text
            if show_alert:
                params["show_alert"] = True
            
            result = await self._make_request("answerCallbackQuery", **params)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"回复回调失败: {e}")
            return False
    
    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """注册消息处理器"""
        try:
            if not handler:
                self.logger.warning("消息处理器未设置")
                return
            
            self.message_handler = handler
            self.logger.info("Telegram消息处理器已注册")
            
        except Exception as e:
            self.logger.error(f"注册消息处理器失败: {e}")
    
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """注册回调处理器"""
        try:
            if not callback_id:
                self.logger.warning("回调ID为空")
                return
            
            self.callback_handlers[callback_id] = handler
            self.logger.info(f"回调处理器已注册: {callback_id}")
            
        except Exception as e:
            self.logger.error(f"注册回调处理器失败: {e}")
    
    async def handle_update(self, update: Dict[str, Any]) -> Optional[Response]:
        """处理Telegram更新(用于webhook)"""
        try:
            # 处理消息
            if "message" in update:
                message_data = update["message"]
                if self.message_handler:
                    msg = Message(
                        content=message_data.get("text", ""),
                        sender_id=str(message_data.get("from", {}).get("id")),
                        metadata=message_data
                    )
                    return await self.message_handler(msg)
            
            # 处理callback_query
            elif "callback_query" in update:
                callback_data = update["callback_query"]
                custom_id = callback_data.get("data", {})
                if custom_id in self.callback_handlers:
                    handler = self.callback_handlers[custom_id]
                    return await handler(callback_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"处理更新失败: {e}")
            return None
    
    async def set_webhook(self, url: str, certificate: str = None) -> bool:
        """设置Webhook"""
        try:
            params = {"url": url}
            if certificate:
                params["certificate"] = certificate
            
            result = await self._make_request("setWebhook", **params)
            if result:
                self.logger.info(f"Webhook已设置: {url}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"设置Webhook失败: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """删除Webhook"""
        try:
            result = await self._make_request("deleteWebhook")
            if result:
                self.logger.info("Webhook已删除")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"删除Webhook失败: {e}")
            return False
    
    async def get_updates(self, offset: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """获取更新(用于polling模式)"""
        try:
            result = await self._make_request("getUpdates", offset=offset, limit=limit)
            return result if result else []
            
        except Exception as e:
            self.logger.error(f"获取更���失���: {e}")
            return []
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.logger.info("Telegram适配器资源已清理")
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")