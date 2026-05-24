"""
邮件网关适配器 - IMAP接收 + SMTP发送
配置项（.env）：
  EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
  EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_USE_SSL (默认True)
"""
import email
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Dict, Any, Optional, Callable, Awaitable, List

import httpx

from . import PlatformAdapter, Message, Response, logger


class EmailAdapter(PlatformAdapter):
    """邮件IMAP+SMTP适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.imap_host: str = config.get("imap_host", "")
        self.imap_port: int = int(config.get("imap_port", 993))
        self.smtp_host: str = config.get("smtp_host", "")
        self.smtp_port: int = int(config.get("smtp_port", 465))
        self.username: str = config.get("username", "")
        self.password: str = config.get("password", "")
        self.use_ssl: bool = config.get("use_ssl", True)

    def get_platform_name(self) -> str:
        return "email"

    async def initialize(self) -> bool:
        try:
            import imaplib
            if self.use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port)
            imap.login(self.username, self.password)
            imap.logout()
            self.bot_info = {"email": self.username}
            logger.info("邮件适配器初始化成功")
            return True
        except Exception as e:
            logger.error(f"邮件初始化失败: {e}")
            return False

    @staticmethod
    def _decode_header_value(value: str) -> str:
        """解码邮件头部"""
        if not value:
            return ""
        parts = decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return "".join(decoded)

    def _email_to_message(self, msg: email.message.Message, msg_id: str = "") -> Message:
        """邮件 → 统一Message"""
        subject = self._decode_header_value(msg.get("Subject", ""))
        from_addr = self._decode_header_value(msg.get("From", ""))
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(charset, errors="replace")
                        break
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(charset, errors="replace")
        return Message(
            msg_id=msg_id,
            platform="email",
            msg_type="text",
            content=f"[{subject}]\n{body}" if subject else body,
            sender={"user_id": from_addr, "email": from_addr},
            room=None,
            raw_data={"subject": subject, "from": from_addr, "body": body},
        )

    async def send_message(self, response: Response, target: Dict[str, Any]) -> bool:
        """通过SMTP发送邮件"""
        import smtplib
        to_addr = target.get("user_id", target.get("email", ""))
        if not to_addr:
            logger.error("邮件发送缺少收件人")
            return False
        subject = target.get("subject", "SerpentAI回复")
        try:
            msg = MIMEMultipart()
            msg["From"] = self.username
            msg["To"] = to_addr
            msg["Subject"] = subject
            if response.msg_type == "markdown" and response.markdown:
                msg.attach(MIMEText(response.markdown, "html", "utf-8"))
            else:
                msg.attach(MIMEText(response.message, "plain", "utf-8"))
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
                smtp.starttls()
            smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    async def send_direct_message(self, user_id: str, response: Response) -> bool:
        return await self.send_message(response, {"email": user_id})

    async def on_message(self, message: Message, handler: Callable[[Message], Awaitable[Response]]) -> None:
        resp = await handler(message)
        target = {"email": message.sender.get("email", ""), "subject": f"Re: {message.raw_data.get('subject', '')}"}
        await self.send_message(resp, target)

    async def on_callback(self, callback_id: str, data: Dict[str, Any], handler: Callable) -> None:
        await handler(data)

    async def cleanup(self) -> None:
        pass  # IMAP/SMTP连接为短连接模式，无需清理
