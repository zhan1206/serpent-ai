"""
LINE Messaging API网关适配器
配置项（.env）：
  LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
"""
import hashlib
import hmac
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class LINEAdapter(PlatformAdapter):
    """LINE Messaging API适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.channel_access_token: str = config.get("channel_access_token", "")
        self.channel_secret: str = config.get("channel_secret", "")
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "line"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url="https://api.line.me/v2/bot/",
            headers={"Authorization": f"Bearer {self.channel_access_token}"},
            timeout=30,
        )
        try:
            resp = await self._client.get("info")
            if resp.status_code == 200:
                data = resp.json()
                self.bot_info = {
                    "bot_id": data.get("userId", ""),
                    "display_name": data.get("displayName", ""),
                }
                logger.info("LINE适配器初始化成功")
                return True
            return False
        except Exception as e:
            logger.error(f"LINE初始化失败: {e}")
            return False

    def _line_event_to_message(self, event: Dict[str, Any]) -> Message:
        """LINE Webhook事件 → 统一Message"""
        source = event.get("source", {})
        msg_type = event.get("message", {}).get("type", "text")
        content = ""
        if msg_type == "text":
            content = event.get("message", {}).get("text", "")
        elif msg_type == "image":
            content = "[图片]"
        elif msg_type == "location":
            content = "[位置]"
        else:
            content = f"[{msg_type}]"
        return Message(
            msg_id=event.get("message", {}).get("id", event.get("timestamp", "")),
            platform="line",
            msg_type=msg_type,
            content=content,
            sender={
                "user_id": source.get("userId", ""),
                "type": source.get("type", ""),
            },
            room={
                "room_id": source.get("groupId", source.get("roomId", "")),
                "type": source.get("type", "user"),
            },
            raw_data=event,
        )

    def _response_to_line_payload(self, response: Response, target: Dict[str, Any]) -> Dict[str, Any]:
        """统一Response → LINE消息体"""
        payload: Dict[str, Any] = {"to": target.get("room_id", target.get("user_id", ""))}
        if response.msg_type == "markdown" and response.markdown:
            payload["messages"] = [{"type": "text", "text": response.markdown}]
        else:
            payload["messages"] = [{"type": "text", "text": response.message}]
        if response.keyboard:
            actions = []
            for item in response.keyboard[:4]:
                label = item.get("label", item.get("text", ""))
                actions.append({"type": "message", "label": label, "text": label})
            if actions:
                payload["messages"].append({
                    "type": "template",
                    "altText": response.message,
                    "template": {"type": "buttons", "text": response.message, "actions": actions},
                })
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        payload = self._response_to_line_payload(response, target)
        if not payload.get("to"):
            logger.error("LINE发送消息缺少目标")
            return False
        try:
            resp = await self._client.post("message/push", json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"LINE发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"user_id": user_id})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        source_type = message.room.get("type", "user") if message.room else "user"
        if source_type == "group":
            target = {"room_id": message.room.get("room_id", "") if message.room else ""}
        else:
            target = {"user_id": message.sender.get("user_id", "")}
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
