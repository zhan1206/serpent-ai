"""
Slack网关适配器 - Slack Bolt API
配置项（.env）：
  SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class SlackAdapter(PlatformAdapter):
    """Slack Bolt API适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token: str = config.get("bot_token", "")
        self.app_token: str = config.get("app_token", "")
        self.signing_secret: str = config.get("signing_secret", "")
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "slack"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url="https://slack.com/api/",
            headers={"Authorization": f"Bearer {self.bot_token}"},
            timeout=30,
        )
        try:
            resp = await self._client.get("auth.test")
            data = resp.json()
            if data.get("ok"):
                self.bot_info = {
                    "bot_id": data.get("bot_id", ""),
                    "team": data.get("team", ""),
                    "user": data.get("user", ""),
                }
                logger.info("Slack适配器初始化成功")
                return True
            else:
                logger.error(f"Slack认证失败: {data.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Slack初始化失败: {e}")
            return False

    def _slack_event_to_message(self, event: Dict[str, Any]) -> Message:
        """Slack事件 → 统一Message"""
        return Message(
            msg_id=event.get("client_msg_id", event.get("ts", "")),
            platform="slack",
            msg_type="text",
            content=event.get("text", ""),
            sender={
                "user_id": event.get("user", ""),
                "channel_id": event.get("channel", ""),
            },
            room={
                "room_id": event.get("channel", ""),
                "thread_ts": event.get("thread_ts", ""),
                "type": "channel" if event.get("channel_type") == "channel" else "im",
            },
            raw_data=event,
        )

    def _response_to_slack_payload(self, response: Response, target: Dict[str, Any]) -> Dict[str, Any]:
        """统一Response → Slack消息体"""
        payload: Dict[str, Any] = {
            "channel": target.get("room_id", ""),
            "text": response.message,
        }
        thread_ts = target.get("thread_ts", "")
        if thread_ts:
            payload["thread_ts"] = thread_ts
        if response.msg_type == "markdown" and response.markdown:
            payload["blocks"] = [
                {"type": "section", "text": {"type": "mrkdwn", "text": response.markdown}}
            ]
        if response.attachments:
            payload["attachments"] = response.attachments
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        payload = self._response_to_slack_payload(response, target)
        try:
            resp = await self._client.post("chat.postMessage", json=payload)
            return resp.json().get("ok", False)
        except Exception as e:
            logger.error(f"Slack发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        try:
            # 打开DM频道
            dm_resp = await self._client.post("conversations.open", json={"users": user_id})
            channel_id = dm_resp.json().get("channel", {}).get("id", "")
            if not channel_id:
                return False
            return await self.send_message(response, {"room_id": channel_id})
        except Exception as e:
            logger.error(f"Slack私信发送失败: {e}")
            return False

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target = {
            "room_id": message.room.get("room_id", "") if message.room else "",
            "thread_ts": message.room.get("thread_ts", "") if message.room else "",
        }
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
