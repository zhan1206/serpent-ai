"""
飞书平台适配器
支持飞书消息、回调、事件处理
"""
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
import logging
import aiohttp
from core.logging_config import get_logger
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
        """处理飞书消息事件（需要通过WebSocket或回调URL接收）"""
        pass
    
    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        """处理飞书回调"""
        pass
    
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