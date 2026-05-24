"""
微信网关适配器 - 支持公众号和企业微信API
配置项（.env）：
  WECHAT_APP_ID, WECHAT_APP_SECRET, WECHAT_TOKEN, WECHAT_ENCODING_AES_KEY
  WEWORK_CORP_ID, WEWORK_AGENT_ID, WEWORK_SECRET
"""
import hashlib
import time
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class WechatAdapter(PlatformAdapter):
    """微信公众号 + 企业微信适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mp_app_id: str = config.get("app_id", "")
        self.mp_app_secret: str = config.get("app_secret", "")
        self.mp_token: str = config.get("token", "")
        self.mp_aes_key: str = config.get("encoding_aes_key", "")
        self.wework_corp_id: str = config.get("corp_id", "")
        self.wework_agent_id: str = config.get("agent_id", "")
        self.wework_secret: str = config.get("wework_secret", "")
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self._wework_token: Optional[str] = None
        self._wework_token_expires: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    def get_platform_name(self) -> str:
        return "wechat"

    async def initialize(self) -> bool:
        self._client = httpx.AsyncClient(timeout=30)
        if self.mp_app_id and self.mp_app_secret:
            try:
                await self._refresh_mp_token()
                self.bot_info = {"mp_app_id": self.mp_app_id, "mode": "mp"}
                logger.info("微信公众号适配器初始化成功")
            except Exception as e:
                logger.error(f"微信公众号初始化失败: {e}")
                return False
        if self.wework_corp_id and self.wework_secret:
            try:
                await self._refresh_wework_token()
                self.bot_info["wework"] = True
                logger.info("企业微信适配器初始化成功")
            except Exception as e:
                logger.error(f"企业微信初始化失败: {e}")
        return True

    async def _refresh_mp_token(self) -> None:
        """刷新公众号 access_token"""
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.mp_app_id,
            "secret": self.mp_app_secret,
        }
        resp = await self._client.get(url, params=params)
        data = resp.json()
        self._access_token = data.get("access_token")
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300

    async def _refresh_wework_token(self) -> None:
        """刷新企业微信 access_token"""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.wework_corp_id}&corpsecret={self.wework_secret}"
        resp = await self._client.get(url)
        data = resp.json()
        self._wework_token = data.get("access_token")
        self._wework_token_expires = time.time() + data.get("expires_in", 7200) - 300

    async def _get_mp_token(self) -> str:
        if not self._access_token or time.time() >= self._token_expires:
            await self._refresh_mp_token()
        return self._access_token  # type: ignore

    async def _get_wework_token(self) -> str:
        if not self._wework_token or time.time() >= self._wework_token_expires:
            await self._refresh_wework_token()
        return self._wework_token  # type: ignore

    @staticmethod
    def _parse_mp_xml(xml_text: str) -> Dict[str, str]:
        """简易公众号XML解析"""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
        return {child.tag: child.text or "" for child in root}

    def _mp_xml_to_message(self, data: Dict[str, str]) -> Message:
        """公众号消息 → 统一Message"""
        return Message(
            msg_id=data.get("MsgId", ""),
            platform="wechat",
            msg_type=data.get("MsgType", "text"),
            content=data.get("Content", data.get("Recognition", "")),
            sender={"user_id": data.get("FromUserName", ""), "type": "mp_user"},
            room={"room_id": data.get("ToUserName", ""), "type": "mp"},
            raw_data=data,
        )

    def _wework_msg_to_message(self, data: Dict[str, Any]) -> Message:
        """企业微信消息 → 统一Message"""
        return Message(
            msg_id=str(data.get("MsgId", "")),
            platform="wechat",
            msg_type=data.get("MsgType", "text"),
            content=data.get("Content", ""),
            sender={"user_id": data.get("FromUserName", ""), "type": "wework_user"},
            room={"room_id": data.get("AgentId", ""), "type": "wework"},
            raw_data=data,
        )

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """发送消息（自动区分公众号/企业微信）"""
        room_type = target.get("type", "mp")
        if room_type == "wework":
            return await self._send_wework_message(response, target)
        return await self._send_mp_message(response, target)

    async def _send_mp_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """公众号客服消息发送"""
        token = await self._get_mp_token()
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
        user_id = target.get("user_id", "")
        payload: Dict[str, Any] = {"touser": user_id, "msgtype": "text"}
        if response.msg_type == "markdown" and response.markdown:
            payload["msgtype"] = "news"
            payload["news"] = {"articles": [{"title": "消息", "description": response.markdown}]}
        else:
            payload["text"] = {"content": response.message}
        resp = await self._client.post(url, json=payload)
        return resp.json().get("errcode", -1) == 0

    async def _send_wework_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """企业微信消息发送"""
        token = await self._get_wework_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        user_id = target.get("user_id", "")
        payload: Dict[str, Any] = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": int(self.wework_agent_id),
        }
        if response.msg_type == "markdown" and response.markdown:
            payload["msgtype"] = "markdown"
            payload["markdown"] = {"content": response.markdown}
        else:
            payload["text"] = {"content": response.message}
        resp = await self._client.post(url, json=payload)
        return resp.json().get("errcode", -1) == 0

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"user_id": user_id, "type": "mp"})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        """处理收到的消息并回复"""
        resp = await handler(message)
        target = {"user_id": message.sender.get("user_id", ""), "type": message.room.get("type", "mp") if message.room else "mp"}
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
