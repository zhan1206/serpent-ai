"""
Webhook通用网关适配器 - 接收外部Webhook并转发消息
配置项（.env）：
  WEBHOOK_SECRET, WEBHOOK_URL (对外暴露的回调地址)
"""
import hashlib
import hmac
import json
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class WebhookAdapter(PlatformAdapter):
    """Webhook通用适配器 - 将任意HTTP请求转换为统一消息"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.secret: str = config.get("secret", "")
        self.callback_url: str = config.get("url", "")
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "webhook"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(timeout=30)
        self.bot_info = {"callback_url": self.callback_url, "secret_set": bool(self.secret)}
        logger.info("Webhook适配器初始化成功")
        return True

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """验证Webhook签名（HMAC-SHA256）"""
        if not self.secret:
            return True
        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _webhook_to_message(self, data: Dict[str, Any], source: str = "") -> Message:
        """Webhook数据 → 统一Message"""
        return Message(
            msg_id=data.get("id", data.get("msg_id", "")),
            platform="webhook",
            msg_type=data.get("type", "text"),
            content=data.get("content", data.get("text", json.dumps(data, ensure_ascii=False))),
            sender={
                "user_id": data.get("sender_id", data.get("from", source)),
                "name": data.get("sender_name", ""),
            },
            room={
                "room_id": data.get("channel_id", data.get("room_id", "")),
                "type": "webhook",
            },
            raw_data=data,
        )

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """向外部Webhook URL发送响应"""
        url = target.get("webhook_url", target.get("callback_url", ""))
        if not url:
            logger.error("Webhook发送缺少目标URL")
            return False
        payload: Dict[str, Any] = {
            "message": response.message,
            "msg_type": response.msg_type,
        }
        if response.markdown:
            payload["markdown"] = response.markdown
        if response.attachments:
            payload["attachments"] = response.attachments
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.secret:
            body = json.dumps(payload, ensure_ascii=False).encode()
            sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = sig
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            return resp.status_code < 300
        except Exception as e:
            logger.error(f"Webhook发送失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"webhook_url": user_id})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        callback_url = message.raw_data.get("callback_url", "")
        if callback_url:
            await self.send_message(resp, {"webhook_url": callback_url})

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
