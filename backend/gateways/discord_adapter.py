"""
Discord平台适配器
支持Discord消息、回调、事件处理
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List
import asyncio
import aiohttp
import logging
import json
from backend.core.logging_config import get_logger
from . import PlatformAdapter, Message, Response

logger = get_logger(__name__)


class DiscordAdapter(PlatformAdapter):
    """Discord平台适配器"""
    
    # Discord API配置
    DISCORD_API_BASE = "https://discord.com/api/v10"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")
        self.guild_id = config.get("guild_id", "")
        self.channel_id = config.get("channel_id", "")
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers: Dict[str, str] = {}
        self.intents = config.get("intents", 513)  # GUILDS + GUILD_MESSAGES
    
    def get_platform_name(self) -> str:
        return "discord"
    
    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "SerpentAI/1.0 (https://github.com/zhan1206/serpent-ai)"
        }
    
    async def initialize(self) -> bool:
        """初始化Discord连接"""
        try:
            # 创建aiohttp session
            self.session = aiohttp.ClientSession()
            self.headers = self._get_headers()
            
            # 验证Bot token - 获取当前用户信息
            async with self.session.get(
                f"{self.DISCORD_API_BASE}/users/@me",
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    self.bot_info = {
                        "bot_id": user_data.get("id"),
                        "username": user_data.get("username"),
                        "bot": user_data.get("bot", True),
                        "guild_id": self.guild_id,
                        "platform": "discord",
                        "connected": True
                    }
                    self.logger.info(f"Discord Bot {user_data.get('username')} 登录成功")
                    return True
                else:
                    error_text = await resp.text()
                    self.logger.error(f"Discord API验证失败: {resp.status} - {error_text}")
                    return False
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"Discord连接错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Discord适配器初始化失败: {e}")
            return False
    
    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到Discord频道"""
        try:
            if not response.content:
                self.logger.warning("响应内容为空")
                return False
            
            channel_id = target.get("channel_id", self.channel_id)
            if not channel_id:
                self.logger.warning("目标频道ID未指定")
                return False
            
            # 构建消息payload
            payload = {
                "content": response.content,
                "tts": response.metadata.get("tts", False)
            }
            
            # 添加embed如果存在
            if response.metadata.get("embeds"):
                payload["embeds"] = response.metadata["embeds"]
            
            # 发送请求
            async with self.session.post(
                f"{self.DISCORD_API_BASE}/channels/{channel_id}/messages",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status in (200, 201):
                    message_data = await resp.json()
                    self.logger.info(f"消息发送到Channel {channel_id}: {message_data.get('id')}")
                    return True
                else:
                    error_text = await resp.text()
                    self.logger.error(f"发送消息失败: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"发送消息异常: {e}")
            return False
    
    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信到Discord用户"""
        try:
            if not user_id:
                self.logger.warning("用户ID为空")
                return False
            
            if not response.content:
                self.logger.warning("响应内容为空")
                return False
            
            # 先创建DM频道
            payload = {"recipient_id": user_id}
            
            async with self.session.post(
                f"{self.DISCORD_API_BASE}/users/@me/channels",
                headers=self.headers,
                json=payload
            ) as resp:
                if resp.status not in (200, 201):
                    error_text = await resp.text()
                    self.logger.error(f"创建DM失败: {resp.status} - {error_text}")
                    return False
                
                dm_data = await resp.json()
                dm_channel_id = dm_data.get("id")
            
            # 发送消息到DM
            message_payload = {"content": response.content}
            
            async with self.session.post(
                f"{self.DISCORD_API_BASE}/channels/{dm_channel_id}/messages",
                headers=self.headers,
                json=message_payload
            ) as resp:
                if resp.status in (200, 201):
                    self.logger.info(f"私信发送到用户 {user_id}")
                    return True
                else:
                    error_text = await resp.text()
                    self.logger.error(f"发送私信失败: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"发送私信异常: {e}")
            return False
    
    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """处理Discord消息"""
        try:
            if not handler:
                self.logger.warning("消息处理器未设置")
                return
            
            # 注册消息处理器
            self.message_handler = handler
            self.logger.info("Discord消息处理器已注册")
            
        except Exception as e:
            self.logger.error(f"注册消息处理器失败: {e}")
    
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """处理Discord回调(Button/Select菜单等)"""
        try:
            if not callback_id:
                self.logger.warning("回调ID为空")
                return
            
            # 存储回调处理器
            if not hasattr(self, 'callback_handlers'):
                self.callback_handlers = {}
            self.callback_handlers[callback_id] = handler
            self.logger.info(f"回调处理器已注册: {callback_id}")
            
        except Exception as e:
            self.logger.error(f"注册回调处理器失败: {e}")
    
    async def handle_interaction(self, interaction_data: Dict[str, Any]) -> Optional[Response]:
        """处理Discord交互(Button点击、Select选择等)"""
        try:
            custom_id = interaction_data.get("data", {}).get("custom_id")
            if custom_id and hasattr(self, 'callback_handlers'):
                handler = self.callback_handlers.get(custom_id)
                if handler:
                    return await handler(interaction_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"处理交互失败: {e}")
            return None
    
    async def get_channel_messages(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取频道消息历史"""
        try:
            async with self.session.get(
                f"{self.DISCORD_API_BASE}/channels/{channel_id}/messages?limit={limit}",
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
                
        except Exception as e:
            self.logger.error(f"获取消息历史失败: {e}")
            return []
    
    async def get_guild_channels(self) -> List[Dict[str, Any]]:
        """获取服务器所有频道"""
        try:
            if not self.guild_id:
                return []
            
            async with self.session.get(
                f"{self.DISCORD_API_BASE}/guilds/{self.guild_id}/channels",
                headers=self.headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
                
        except Exception as e:
            self.logger.error(f"获取频道列表失败: {e}")
            return []
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.logger.info("Discord适配器资源已清理")
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")