"""
飞书平台适配器
支持飞书消息、回调、事件处理
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime
import logging
import aiohttp
from backend.core.logging_config import get_logger
from . import PlatformAdapter, Message, Response

logger = get_logger(__name__)


class FeishuAdapter(PlatformAdapter):
    """飞书平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id", "")
        self.app_secret = config.get("app_secret", "")
        self.verification_token = config.get("verification_token", "")
        self.host = config.get("host", "https://open.feishu.cn")
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    def get_platform_name(self) -> str:
        return "feishu"
    
    async def initialize(self) -> bool:
        """初始化飞书连接"""
        try:
            self.session = aiohttp.ClientSession()
            success = await self._get_access_token()
            
            if success:
                self.bot_info = {
                    "app_id": self.app_id,
                    "platform": "feishu",
                    "connected": True
                }
                self.logger.info(f"飞书适配器初始化成功: {self.app_id}")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"飞书适配器初始化失败: {e}")
            return False
    
    async def _get_access_token(self) -> bool:
        """获取飞书访问令牌"""
        try:
            url = f"{self.host}/open-apis/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            async with self.session.post(url, json=payload) as resp:
                data = await resp.json()
                
                if resp.status == 200 and data.get("msg") == "success":
                    self.access_token = data.get("tenant_access_token")
                    # 令牌有效期2小时，设置提前5分钟过期
                    self.token_expires_at = datetime.now()
                    return True
                
                self.logger.error(f"获取飞书令牌失败: {data}")
                return False
        except Exception as e:
            self.logger.error(f"获取飞书令牌异常: {e}")
            return False
    
    async def _ensure_token(self) -> bool:
        """确保令牌有效"""
        if not self.access_token or not self.token_expires_at:
            return await self._get_access_token()
        
        # 检查令牌是否快过期
        if (self.token_expires_at - datetime.now()).seconds < 300:
            return await self._get_access_token()
        
        return True
    
    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到飞书"""
        try:
            if not await self._ensure_token():
                return False
            
            chat_id = target.get("chat_id")
            if not chat_id:
                self.logger.error("缺少chat_id")
                return False
            
            # 构建消息内容
            msg_content = self._build_message_content(response)
            
            url = f"{self.host}/open-apis/im/v1/messages"
            params = {"receive_id_type": "chat_id"}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            payload = {
                "receive_id": chat_id,
                "msg_type": response.msg_type,
                "content": msg_content
            }
            
            async with self.session.post(url, params=params, headers=headers, json=payload) as resp:
                data = await resp.json()
                return resp.status == 200 and data.get("msg") == "success"
        except Exception as e:
            self.logger.error(f"发送飞书消息失败: {e}")
            return False
    
    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信到飞书"""
        try:
            if not await self._ensure_token():
                return False
            
            msg_content = self._build_message_content(response)
            
            url = f"{self.host}/open-apis/im/v1/messages"
            params = {"receive_id_type": "open_id"}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            payload = {
                "receive_id": user_id,
                "msg_type": response.msg_type,
                "content": msg_content
            }
            
            async with self.session.post(url, params=params, headers=headers, json=payload) as resp:
                data = await resp.json()
                return resp.status == 200 and data.get("msg") == "success"
        except Exception as e:
            self.logger.error(f"发送飞书私信失败: {e}")
            return False
    
    def _build_message_content(self, response: Response) -> str:
        """构建消息内容"""
        if response.msg_type == "text":
            import json
            return json.dumps({"text": response.message})
        elif response.msg_type == "post":
            import json
            return json.dumps({
                "zh_cn": {
                    "title": response.meta.get("title", ""),
                    "content": [[{"tag": "text", "text": response.message}]]
                }
            })
        elif response.msg_type == "interactive":
            import json
            return json.dumps({
                "config": {"wide_screen_mode": True},
                "elements": [
                    {"tag": "markdown", "content": response.message}
                ]
            })
        else:
            import json
            return json.dumps({"text": response.message})
    
    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """注册消息处理器"""
        try:
            if not handler:
                self.logger.warning("消息处理器未设置")
                return
            
            self.message_handler = handler
            self.logger.info("飞书消息处理器已注册")
            
        except Exception as e:
            self.logger.error(f"注册消息处理器失败: {e}")
    
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """注册回调处理器(飞书卡片操作等)"""
        try:
            if not callback_id:
                self.logger.warning("回调ID为空")
                return
            
            if not hasattr(self, 'callback_handlers'):
                self.callback_handlers = {}
            self.callback_handlers[callback_id] = handler
            self.logger.info(f"回调处理器已注册: {callback_id}")
            
        except Exception as e:
            self.logger.error(f"注册回调处理器失败: {e}")
    
    async def handle_webhook_event(self, event: Dict[str, Any]) -> Optional[Response]:
        """处理Webhook事件(接收飞书回调)"""
        try:
            event_type = event.get("type")
            
            if event_type == "url_verification":
                # URL验证 - 返回challenge
                return Response(
                    message="",
                    msg_type="json",
                    meta={"challenge": event.get("challenge", "")}
                )
            elif event_type == "im.message.receive_v1":
                # 接收消息事件
                message_data = event.get("message", {})
                msg = Message(
                    msg_id=message_data.get("message_id", ""),
                    content=message_data.get("text_content", ""),
                    sender_id=message_data.get("sender_id", {}).get("open_id", ""),
                    metadata=event
                )
                if hasattr(self, 'message_handler') and self.message_handler:
                    return await self.message_handler(msg)
                return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"处理Webhook事件失败: {e}")
            return None
    
    async def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片到飞书"""
        try:
            if not await self._ensure_token():
                return None
            
            url = f"{self.host}/open-apis/im/v1/images"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            data = aiohttp.FormData()
            data.add_field('image_type', 'message')
            with open(image_path, 'rb') as f:
                data.add_field('image', f, filename=image_path)
                
            async with self.session.post(url, headers=headers, data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("msg") == "success":
                        return result.get("data", {}).get("image_key")
            return None
            
        except Exception as e:
            self.logger.error(f"上传图片失败: {e}")
            return None
    
    async def get_chat_info(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """获取群聊信息"""
        try:
            if not await self._ensure_token():
                return None
            
            url = f"{self.host}/open-apis/im/v1/chats/{chat_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("msg") == "success":
                        return data.get("data", {})
            return None
            
        except Exception as e:
            self.logger.error(f"获取群聊信息失败: {e}")
            return None
    
    async def create_chat(self, name: str, user_ids: List[str]) -> Optional[str]:
        """创建群聊"""
        try:
            if not await self._ensure_token():
                return None
            
            url = f"{self.host}/open-apis/im/v1/chats"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            payload = {
                "name": name,
                "user_id_list": user_ids,
                "chat_type": "group"
            }
            
            async with self.session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("msg") == "success":
                        return data.get("data", {}).get("chat_id")
            return None
            
        except Exception as e:
            self.logger.error(f"创建群聊失败: {e}")
            return None
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
        self.access_token = None
        self.logger.info("飞书适配器已清理")


# ==================== 飞书事件处理器 ====================

class FeishuEventHandler:
    """飞书事件处理器"""
    
    def __init__(self, adapter: FeishuAdapter):
        self.adapter = adapter
    
    async def handle_event(self, event: Dict[str, Any]) -> Optional[Response]:
        """处理飞书事件"""
        event_type = event.get("type")
        
        if event_type == "url_verification":
            # URL验证
            return Response(
                message="",
                msg_type="json",
                meta={"challenge": event.get("challenge", "")}
            )
        elif event_type == "im.message.receive_v1":
            # 接收消息
            message = self._parse_message(event)
            return None  # 返回None表示需要进一步处理
        elif event_type == "im.message.p2p Receive":
            # 接收私信
            message = self._parse_p2p_message(event)
            return None
        
        return None
    
    def _parse_message(self, event: Dict[str, Any]) -> Message:
        """解析消息事件"""
        message_data = event.get("message", {})
        
        return Message(
            msg_id=message_data.get("message_id", ""),
            platform="feishu",
            msg_type=message_data.get("msg_type", "text"),
            content=message_data.get("text_content", ""),
            sender={
                "user_id": message_data.get("sender_id", {}).get("open_id", ""),
                "tenant_id": message_data.get("sender_id", {}).get("tenant_id", "")
            },
            room={
                "chat_id": message_data.get("chat_id", "")
            },
            raw_data=event
        )
    
    def _parse_p2p_message(self, event: Dict[str, Any]) -> Message:
        """解析私信事件"""
        return Message(
            msg_id=event.get("message_id", ""),
            platform="feishu",
            msg_type="text",
            content=event.get("text_content", ""),
            sender={
                "user_id": event.get("open_id", "")
            },
            raw_data=event
        )