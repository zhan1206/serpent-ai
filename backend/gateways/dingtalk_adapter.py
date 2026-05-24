"""
钉钉网关适配器 - Stream API模式
配置项（.env）：
  DINGTALK_CLIENT_ID, DINGTALK_CLIENT_SECRET, DINGTALK_ROBOT_CODE
"""
import hashlib
import hmac
import base64
import time
import urllib.parse
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class DingtalkAdapter(PlatformAdapter):
    """钉钉Stream API适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id: str = config.get("client_id", "")
        self.client_secret: str = config.get("client_secret", "")
        self.robot_code: str = config.get("robot_code", "")
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "dingtalk"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(timeout=30)
        try:
            await self._refresh_token()
            self.bot_info = {"client_id": self.client_id, "robot_code": self.robot_code}
            logger.info("钉钉适配器初始化成功")
            return True
        except Exception as e:
            logger.error(f"钉钉初始化失败: {e}")
            return False

    async def _refresh_token(self) -> None:
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        resp = await self._client.post(url, json={
            "appKey": self.client_id,
            "appSecret": self.client_secret,
        })
        data = resp.json()
        self._access_token = data.get("accessToken")
        self._token_expires = time.time() + data.get("expireIn", 7200) - 300

    async def _get_token(self) -> str:
        if not self._access_token or time.time() >= self._token_expires:
            await self._refresh_token()
        return self._access_token  # type: ignore

    def _dingtalk_msg_to_message(self, data: Dict[str, Any]) -> Message:
        """钉钉消息 → 统一Message"""
        sender = data.get("sender", {})
        conversation = data.get("conversation", {})
        text_content = data.get("text", {}).get("content", "")
        msg_type = data.get("msgtype", "text")
        return Message(
            msg_id=data.get("messageId", ""),
            platform="dingtalk",
            msg_type=msg_type,
            content=text_content.strip(),
            sender={
                "user_id": sender.get("senderId", ""),
                "nick": sender.get("senderNick", ""),
                "staff_id": sender.get("senderStaffId", ""),
            },
            room={
                "room_id": conversation.get("conversationId", ""),
                "type": conversation.get("conversationType", ""),
                "title": conversation.get("title", ""),
            },
            raw_data=data,
        )

    def _response_to_dingtalk_payload(self, response: Response, conversation_id: str) -> Dict[str, Any]:
        """统一Response → 钉钉消息体"""
        payload: Dict[str, Any] = {
            "robotCode": self.robot_code,
            "conversationId": conversation_id,
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["msgKey"] = "sampleMarkdown"
            payload["msgParam"] = str({"title": "消息", "text": response.markdown})
        else:
            payload["msgKey"] = "sampleText"
            payload["msgParam"] = str({"content": response.message})
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        token = await self._get_token()
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        headers = {"x-acs-dingtalk-access-token": token}
        conversation_id = target.get("room_id", "")
        if not conversation_id:
            logger.error("钉钉发送消息缺少conversation_id")
            return False
        payload = self._response_to_dingtalk_payload(response, conversation_id)
        user_ids = target.get("user_ids", [target.get("staff_id", "")])
        payload["userIds"] = [uid for uid in user_ids if uid]
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"钉钉发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        token = await self._get_token()
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        headers = {"x-acs-dingtalk-access-token": token}
        payload: Dict[str, Any] = {
            "robotCode": self.robot_code,
            "userIds": [user_id],
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["msgKey"] = "sampleMarkdown"
            payload["msgParam"] = str({"title": "消息", "text": response.markdown})
        else:
            payload["msgKey"] = "sampleText"
            payload["msgParam"] = str({"content": response.message})
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"钉钉私信发送失败: {e}")
            return False

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target = {
            "room_id": message.room.get("room_id", "") if message.room else "",
            "staff_id": message.sender.get("staff_id", ""),
        }
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
