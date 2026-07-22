"""Background workers that keep network and reservation work off the UI thread."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal, Slot
from korail2 import ReserveOption, TrainType

from config.settings import settings
from services.korail_service import DuplicateReservationError, KorailService
from services.credential_service import CredentialService
from services.google_oauth_service import GoogleOAuthNotification, authenticate
from services.notification_service import NotificationPipeline, TelegramNotification


@dataclass(frozen=True)
class ReservationRequest:
    username: str
    password: str
    source: str
    destination: str
    date: str
    after: str
    before: str
    passengers: int
    train_type: TrainType
    reserve_option: ReserveOption
    strategy: str
    email_recipient: str = ""
    google_token: str = ""
    email_enabled: bool = False
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""


class ReservationWorker(QObject):
    status = Signal(str)
    progress = Signal(int, str)
    succeeded = Signal(str)
    failed = Signal(str)
    login_checked = Signal(bool, str)
    finished = Signal()

    def __init__(self, request: ReservationRequest, login_only: bool = False):
        super().__init__()
        self.request = request
        self.login_only = login_only
        self.cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        pipeline = self._pipeline()
        try:
            self.status.emit("코레일에 로그인 중...")
            service = KorailService()
            if not service.login(self.request.username, self.request.password):
                message = "회원번호/아이디, 비밀번호 또는 계정 상태를 확인하세요."
                self._notify(pipeline, "코레일 로그인 실패", message)
                self.login_checked.emit(False, message)
                if not self.login_only:
                    self.failed.emit(message)
                return
            self.login_checked.emit(True, "로그인에 성공했습니다.")
            if self.login_only:
                return

            self.status.emit("좌석을 검색하고 있습니다...")
            reservation = service.search_and_reserve_loop(
                dep_date=self.request.date,
                src_locate=self.request.source,
                dst_locate=self.request.destination,
                dep_time=self.request.after,
                max_dep_time=self.request.before,
                train_type=self.request.train_type,
                reserve_option=self.request.reserve_option,
                passenger_count=self.request.passengers,
                seat_strategy=self.request.strategy,
                cancel_event=self.cancel_event,
                progress_callback=self._on_progress,
            )
            if self.cancel_event.is_set():
                self.status.emit("사용자가 예약 검색을 중지했습니다.")
                return
            if not reservation:
                self.failed.emit("예약 결과를 받지 못했습니다.")
                return

            message = (
                f"예약 성공\n\n{reservation}\n\n"
                f"{settings.PAYMENT_TIMEOUT_MINUTES}분 이내에 코레일 사이트/앱에서 결제하세요.\n"
                f"{settings.KORAIL_PAYMENT_URL}"
            )
            self._notify(pipeline, "코레일 예약 성공", message)
            self.succeeded.emit(message)
        except DuplicateReservationError:
            self.failed.emit("동일한 예약이 이미 있습니다. 코레일 예약 내역을 확인하세요.")
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self._notify(pipeline, "코레일 자동예약 오류", message)
            self.failed.emit(message)
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        self.cancel_event.set()

    def _on_progress(self, info: dict) -> None:
        from datetime import datetime
        timestamp = datetime.fromtimestamp(info["timestamp"]).strftime("%H:%M:%S")
        self.progress.emit(info["attempts"], timestamp)

    def _pipeline(self) -> NotificationPipeline:
        channels = []
        if self.request.email_enabled and self.request.google_token and self.request.email_recipient:
            channels.append(GoogleOAuthNotification(
                    self.request.google_token,
                    self.request.email_recipient,
                    token_updated=lambda token: CredentialService().set("google_oauth_token", token),
                ))
        if self.request.telegram_enabled and self.request.telegram_token and self.request.telegram_chat_id:
            channels.append(TelegramNotification(self.request.telegram_token, self.request.telegram_chat_id))
        return NotificationPipeline(channels)

    def _notify(self, pipeline: NotificationPipeline, title: str, message: str) -> None:
        results = pipeline.send(title, message)
        if results and not all(results):
            self.status.emit("일부 완료 알림 발송에 실패했습니다. 알림 설정을 확인하세요.")


class EmailTestThread(QThread):
    completed = Signal(bool, str)

    def __init__(self, token_json: str, recipient: str):
        super().__init__()
        self.channel = GoogleOAuthNotification(
            token_json,
            recipient,
            token_updated=lambda token: CredentialService().set("google_oauth_token", token),
        )

    def run(self) -> None:
        try:
            ok, detail = self.channel.send_detailed(
                "코레일 GUI 테스트", "Gmail 알림 설정이 정상입니다."
            )
            message = "테스트 메일을 보냈습니다." if ok else detail
            self.completed.emit(ok, message)
        except Exception as exc:
            self.completed.emit(False, f"이메일 테스트 오류: {type(exc).__name__}: {exc}")


class TelegramTestThread(QThread):
    completed = Signal(bool, str)

    def __init__(self, bot_token: str, chat_id: str):
        super().__init__()
        self.channel = TelegramNotification(bot_token, chat_id)

    def run(self) -> None:
        ok, detail = self.channel.send_detailed("코레일 GUI 테스트", "Telegram 알림 설정이 정상입니다.")
        self.completed.emit(ok, "테스트 메시지를 보냈습니다." if ok else detail)


class GoogleLoginThread(QThread):
    completed = Signal(bool, str, str, str)

    def __init__(self, client_secrets_file: str):
        super().__init__()
        self.client_secrets_file = client_secrets_file

    def run(self) -> None:
        try:
            token, email = authenticate(self.client_secrets_file)
            self.completed.emit(True, token, email, f"Google Gmail 연동이 완료되었습니다.\n알림 주소: {email}")
        except Exception as exc:
            self.completed.emit(False, "", "", f"Google 로그인 실패: {type(exc).__name__}: {exc}")
