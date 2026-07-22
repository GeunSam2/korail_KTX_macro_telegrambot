"""Google desktop OAuth and Gmail API sending."""
from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from typing import Callable, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]


def authenticate(client_secrets_file: str) -> tuple[str, str]:
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        open_browser=True,
        authorization_prompt_message="Google 로그인 화면을 브라우저에서 여는 중입니다...",
        success_message="Google Gmail 연동이 완료되었습니다. 이 창을 닫고 KTX 자동예약 앱으로 돌아가세요.",
    )
    identity = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
    email = identity.userinfo().get().execute()["email"]
    return credentials.to_json(), email


class GoogleOAuthNotification:
    def __init__(
        self,
        token_json: str,
        recipient: str,
        token_updated: Optional[Callable[[str], None]] = None,
    ):
        self.token_json = token_json
        self.recipient = recipient.strip()
        self.token_updated = token_updated

    def send(self, title: str, message: str) -> bool:
        ok, _ = self.send_detailed(title, message)
        return ok

    def send_detailed(self, title: str, message: str) -> tuple[bool, str]:
        try:
            credentials = Credentials.from_authorized_user_info(
                json.loads(self.token_json), SCOPES
            )
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.token_json = credentials.to_json()
                if self.token_updated:
                    self.token_updated(self.token_json)
            if not credentials.valid:
                return False, "Google 로그인이 만료되었습니다. Google 로그인 버튼을 다시 누르세요."

            email = EmailMessage()
            email["To"] = self.recipient
            email["Subject"] = title
            email.set_content(message)
            raw = base64.urlsafe_b64encode(email.as_bytes()).decode("ascii")
            service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return True, "발송 성공"
        except (ValueError, json.JSONDecodeError):
            return False, "저장된 Google 로그인 정보가 올바르지 않습니다. 다시 로그인하세요."
        except HttpError as exc:
            if exc.resp.status in (401, 403):
                return False, "Google Gmail 권한이 없거나 만료되었습니다. 다시 로그인하세요."
            return False, f"Gmail API 오류: HTTP {exc.resp.status}"
        except (TimeoutError, OSError):
            return False, "Google Gmail 서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요."
        except Exception as exc:
            return False, f"Google Gmail 오류: {type(exc).__name__}: {exc}"
