"""Notification channels for the desktop application."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable, Protocol

import requests


class NotificationChannel(Protocol):
    def send(self, title: str, message: str) -> bool: ...


class GmailNotification:
    def __init__(self, sender: str, app_password: str, recipient: str):
        self.sender = sender.strip()
        self.app_password = app_password.replace(" ", "")
        self.recipient = recipient.strip()

    def send(self, title: str, message: str) -> bool:
        ok, _ = self.send_detailed(title, message)
        return ok

    def send_detailed(self, title: str, message: str) -> tuple[bool, str]:
        email = EmailMessage()
        email["Subject"] = title
        email["From"] = self.sender
        email["To"] = self.recipient
        email.set_content(message)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as client:
                client.login(self.sender, self.app_password)
                client.send_message(email)
            return True, "발송 성공"
        except smtplib.SMTPAuthenticationError:
            return False, (
                "Gmail이 인증을 거부했습니다. 일반 Google 계정 비밀번호가 아니라 "
                "2단계 인증을 켠 뒤 생성한 16자리 '앱 비밀번호'를 입력하세요."
            )
        except (TimeoutError, OSError):
            return False, "Gmail 서버에 연결할 수 없습니다. 인터넷 연결과 방화벽을 확인하세요."
        except smtplib.SMTPException as exc:
            return False, f"Gmail SMTP 오류: {type(exc).__name__}"
        except Exception as exc:
            return False, f"이메일 오류: {type(exc).__name__}: {exc}"


class TelegramNotification:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()

    def send(self, title: str, message: str) -> bool:
        ok, _ = self.send_detailed(title, message)
        return ok

    def send_detailed(self, title: str, message: str) -> tuple[bool, str]:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": f"{title}\n\n{message}"},
                timeout=15,
            )
            response.raise_for_status()
            if not response.json().get("ok", False):
                return False, "Telegram이 메시지 발송을 거부했습니다."
            return True, "발송 성공"
        except requests.RequestException as exc:
            return False, f"Telegram 통신 오류: {type(exc).__name__}"
        except Exception as exc:
            return False, f"Telegram 오류: {type(exc).__name__}: {exc}"


class NotificationPipeline:
    def __init__(self, channels: Iterable[NotificationChannel] = ()):
        self.channels = list(channels)

    def send(self, title: str, message: str) -> list[bool]:
        results = []
        for channel in self.channels:
            try:
                results.append(channel.send(title, message))
            except Exception:
                results.append(False)
        return results
