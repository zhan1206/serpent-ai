"""
Signal网关适配器 - signal-cli REST API
配置项（.env）：
  SIGNAL_PHONE_NUMBER, SIGNAL_API_URL (默认 http://localhost:8080)
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class SignalAdapter(PlatformAdapter):
    """Signal (signal-cli) 适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.phone_number: str = config.get("phone_number", "")
        self.api_url: str = config.get("api_url", "http://localhost:8080")
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "signal"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(base_url=self.api_url, timeout=30)
        try:
            resp = await self._client.get(f"/v1/accounts/{self.phone_number}")
            if resp.status_code == 204 or resp.status_code == 200:
                self.bot_info = {"phone_number": self.phone_number, "api_url": self.api_url}
                logger.info("Signal适配器初始化成功")
                return True
            logger.error(f"Signal账号未注册: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Signal初始化失败: {e}")
            return False

    def _signal_msg_to_message(self, data: Dict[str, Any], source: str = "") -> Message:
        """Signal消息 → 统一Message"""
        envelope = data.get("envelope", data)
        return Message(
            msg_id=envelope.get("timestamp", ""),
            platform="signal",
            msg_type="text",
            content=envelope.get("dataMessage", {}).get("message", ""),
            sender={
                "user_id": envelope.get("source", source),
                "source_number": envelope.get("sourceNumber", ""),
                "source_name": envelope.get("sourceName", ""),
            },
            room={
                "room_id": envelope.get("dataMessage", {}).get("groupInfo", {}).get("groupId", ""),
                "type": "group" if envelope.get("dataMessage", {}).get("groupInfo") else "direct",
            },
            raw_data=data,
        )

    def _response_to_signal_payload(self, response: Response, target: str) -> Dict[str, Any]:
        """统一Response → Signal消息体"""
        payload: Dict[str, Any] = {
            "message": response.message,
            "account": self.phone_number,
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["message"] = response.markdown
        if response.attachments:
            first = response.attachments[0]
            if isinstance(first, dict):
                payload["base64_attachments"] = [first]
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        recipient = target.get("user_id", target.get("room_id", ""))
        if not recipient:
            logger.error("Signal发送消息缺少收件人")
            return False
        payload = self._response_to_signal_payload(response, recipient)
        try:
            resp = await self._client.put(f"/v2/send/{recipient}", json=payload)
            return resp.status_code == 201 or resp.status_code == 200
        except Exception as e:
            logger.error(f"Signal发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"user_id": user_id})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target_type = message.room.get("type", "direct") if message.room else "direct"
        if target_type == "group":
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
