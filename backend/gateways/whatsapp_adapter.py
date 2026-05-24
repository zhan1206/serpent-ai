"""
WhatsApp Business API网关适配器
配置项（.env）：
  WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN, WHATSAPP_WABA_ID
"""
import json
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class WhatsAppAdapter(PlatformAdapter):
    """WhatsApp Business API适配器（Cloud API）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.phone_number_id: str = config.get("phone_number_id", "")
        self.access_token: str = config.get("access_token", "")
        self.verify_token: str = config.get("verify_token", "")
        self.waba_id: str = config.get("waba_id", "")
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "whatsapp"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(
            base_url=f"https://graph.facebook.com/v18.0/{self.phone_number_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )
        try:
            resp = await self._client.get(f"https://graph.facebook.com/v18.0/{self.waba_id}?fields=name")
            data = resp.json()
            self.bot_info = {
                "waba_id": self.waba_id,
                "business_name": data.get("name", ""),
                "phone_number_id": self.phone_number_id,
            }
            logger.info("WhatsApp适配器初始化成功")
            return True
        except Exception as e:
            logger.error(f"WhatsApp初始化失败: {e}")
            return False

    def _whatsapp_msg_to_message(self, data: Dict[str, Any]) -> Message:
        """WhatsApp Webhook消息 → 统一Message"""
        entry = data.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        msg = change.get("value", {}).get("messages", [{}])[0] if change.get("value", {}).get("messages") else {}
        contact = change.get("value", {}).get("contacts", [{}])[0] if change.get("value", {}).get("contacts") else {}
        msg_type = msg.get("type", "text")
        content = ""
        if msg_type == "text":
            content = msg.get("text", {}).get("body", "")
        elif msg_type == "image":
            content = msg.get("image", {}).get("caption", "[图片]")
        elif msg_type == "document":
            content = msg.get("document", {}).get("caption", "[文件]")
        elif msg_type == "audio":
            content = "[语音]"
        elif msg_type == "location":
            loc = msg.get("location", {})
            content = f"[位置] {loc.get('latitude')},{loc.get('longitude')}"
        return Message(
            msg_id=msg.get("id", ""),
            platform="whatsapp",
            msg_type=msg_type,
            content=content,
            sender={
                "user_id": msg.get("from", ""),
                "name": contact.get("profile", {}).get("name", ""),
            },
            room=None,
            raw_data=data,
        )

    def _response_to_whatsapp_payload(self, response: Response, recipient: str) -> Dict[str, Any]:
        """统一Response → WhatsApp消息体"""
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"body": response.message},
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["type"] = "text"
            payload["text"]["body"] = response.markdown
        if response.attachments:
            first = response.attachments[0]
            if isinstance(first, dict):
                att_type = first.get("type", "image")
                payload["type"] = att_type
                payload[att_type] = {"link": first.get("url", ""), "caption": first.get("caption", "")}
        return payload

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        recipient = target.get("user_id", target.get("to", ""))
        if not recipient:
            logger.error("WhatsApp发送消息缺少收件人")
            return False
        payload = self._response_to_whatsapp_payload(response, recipient)
        try:
            resp = await self._client.post("/messages", json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"WhatsApp发送消息失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"user_id": user_id})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target = {"user_id": message.sender.get("user_id", "")}
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
