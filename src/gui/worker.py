"""Background workers that keep network and reservation work off the UI thread."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot
from korail2 import ReserveOption, TrainType

from config.settings import settings
from services.korail_service import DuplicateReservationError, KorailService
from services.notification_service import GmailNotification, NotificationPipeline


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
    email_sender: str = ""
    email_password: str = ""
    email_recipient: str = ""


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
        if all((self.request.email_sender, self.request.email_password, self.request.email_recipient)):
            return NotificationPipeline([
                GmailNotification(
                    self.request.email_sender,
                    self.request.email_password,
                    self.request.email_recipient,
                )
            ])
        return NotificationPipeline()

    def _notify(self, pipeline: NotificationPipeline, title: str, message: str) -> None:
        results = pipeline.send(title, message)
        if results and not all(results):
            self.status.emit("이메일 알림 발송에 실패했습니다. Gmail 설정을 확인하세요.")


class EmailTestWorker(QObject):
    completed = Signal(bool)
    finished = Signal()

    def __init__(self, sender: str, password: str, recipient: str):
        super().__init__()
        self.channel = GmailNotification(sender, password, recipient)

    @Slot()
    def run(self) -> None:
        self.completed.emit(self.channel.send("코레일 GUI 테스트", "Gmail 알림 설정이 정상입니다."))
        self.finished.emit()
