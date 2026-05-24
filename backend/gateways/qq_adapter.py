"""
QQ频道Bot网关适配器
配置项（.env）：
  QQ_BOT_APP_ID, QQ_BOT_TOKEN, QQ_BOT_INTENTS
"""
import json
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class QQAdapter(PlatformAdapter):
    """QQ频道Bot适配器 - QQ开放平台API"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id: str = config.get("app_id", "")
        self.token: str = config.get("token", "")
        self.intents: int = config.get("intents", 1 << 25 | 1 << 30)  # GUILD_MESSAGES + INTERACTION
        self._access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._ws_url: Optional[str] = None
        self._session_id: Optional[str] = None

    def get_platform_name(self) -> str:
        return "qq"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url="https://api.sgroup.qq.com",
            headers={"Authorization": f"Bot {self.app_id}.{self.token}"},
            timeout=30,
        )
        try:
            resp = await self._client.get("/gateway")
            data = resp.json()
            self._ws_url = data.get("url")
            self.bot_info = {"app_id": self.app_id, "ws_url": self._ws_url}
            logger.info("QQ频道Bot适配器初始化成功")
            return True
        except Exception as e:
            logger.error(f"QQ频道Bot初始化失败: {e}")
            return False

    def _qq_msg_to_message(self, data: Dict[str, Any]) -> Message:
        """QQ频道消息 → 统一Message"""
        author = data.get("author", {})
        content = data.get("content", "")
        # 处理附件内容
        attachments = data.get("attachments", [])
        if attachments:
            urls = [a.get("url", "") for a in attachments]
            content += "\n" + "\n".join(urls)
        return Message(
            msg_id=data.get("id", ""),
            platform="qq",
            msg_type=data.get("type", 0) and "text" or "text",
            content=content.strip(),
            sender={
                "user_id": author.get("user_openid", author.get("id", "")),
                "username": author.get("username", ""),
            },
            room={
                "room_id": data.get("channel_id", ""),
                "guild_id": data.get("guild_id", ""),
                "type": "qq_channel",
            },
            raw_data=data,
        )

    def _response_to_qq_payload(self, response: Response, channel_id: str) -> Dict[str, Any]:
        """统一Response → QQ消息体"""
        payload: Dict[str, Any] = {
            "content": response.message,
            "msg_type": 0,  # 文本
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["msg_type"] = 2  # markdown
            payload["markdown"] = {"content": response.markdown}
        if response.keyboard:
            payload["keyboard"] = {"content": {"rows": response.keyboard}}
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息到QQ频道"""
        channel_id = target.get("room_id", target.get("channel_id", ""))
        if not channel_id:
            logger.error("QQ发送消息缺少channel_id")
            return False
        payload = self._response_to_qq_payload(response, channel_id)
        msg_type = target.get("msg_type", "normal")
        if msg_type == "direct":
            guild_id = target.get("guild_id", "")
            url = f"/dms/{guild_id}/messages"
        else:
            url = f"/channels/{channel_id}/messages"
        try:
            resp = await self._client.post(url, json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"QQ发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        """发送私信"""
        try:
            dms_resp = await self._client.post(
                "/users/@me/dms",
                json={"recipient_id": user_id},
            )
            guild_id = dms_resp.json().get("guild_id", "")
            return await self.send_message(response, {"guild_id": guild_id, "msg_type": "direct"})
        except Exception as e:
            logger.error(f"QQ私信发送失败: {e}")
            return False

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target = {
            "channel_id": message.room.get("room_id", "") if message.room else "",
            "guild_id": message.room.get("guild_id", "") if message.room else "",
        }
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
