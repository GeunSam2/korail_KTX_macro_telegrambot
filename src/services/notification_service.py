"""Notification channels for the desktop application."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable, Protocol


class NotificationChannel(Protocol):
    def send(self, title: str, message: str) -> bool: ...


class GmailNotification:
    def __init__(self, sender: str, app_password: str, recipient: str):
        self.sender = sender.strip()
        self.app_password = app_password.replace(" ", "")
        self.recipient = recipient.strip()

    def send(self, title: str, message: str) -> bool:
        email = EmailMessage()
        email["Subject"] = title
        email["From"] = self.sender
        email["To"] = self.recipient
        email.set_content(message)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as client:
                client.login(self.sender, self.app_password)
                client.send_message(email)
            return True
        except (OSError, smtplib.SMTPException):
            return False


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
