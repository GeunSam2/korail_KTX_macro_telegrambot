"""Main desktop window for non-technical Korail users."""
from __future__ import annotations

import re
import webbrowser
from datetime import date, timedelta

from PySide6.QtCore import QDate, QSettings, QThread, QTime, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)
from korail2 import ReserveOption, TrainType

from config.settings import settings
from gui.worker import EmailTestThread, ReservationRequest, ReservationWorker
from services.credential_service import CredentialService
from utils.station_codes import FALLBACK_STATIONS


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KTX 자동예약")
        self.resize(780, 760)
        self.settings = QSettings("Celenort", "KorailKTXDesktop")
        self.credentials = CredentialService()
        self.thread: QThread | None = None
        self.worker: ReservationWorker | None = None
        self.email_thread: QThread | None = None
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._reservation_tab(), "예약")
        tabs.addTab(self._notification_tab(), "이메일 알림")
        self.setCentralWidget(tabs)

    def _reservation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        account = QGroupBox("코레일 계정")
        account_form = QFormLayout(account)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_password = QCheckBox("비밀번호 표시")
        self.show_password.toggled.connect(
            lambda checked: self.password.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        self.save_account = QCheckBox("Windows 자격 증명 관리자에 계정 저장")
        account_form.addRow("회원번호/아이디", self.username)
        account_form.addRow("비밀번호", self.password)
        account_form.addRow("", self.show_password)
        account_form.addRow("", self.save_account)
        layout.addWidget(account)

        search = QGroupBox("열차 조건")
        form = QFormLayout(search)
        stations = sorted(FALLBACK_STATIONS)
        self.source = QComboBox(); self.source.setEditable(True); self.source.addItems(stations)
        self.destination = QComboBox(); self.destination.setEditable(True); self.destination.addItems(stations)
        self.source.setCurrentText("광명"); self.destination.setCurrentText("오송")
        self.travel_date = QDateEdit(QDate.currentDate().addDays(1))
        self.travel_date.setCalendarPopup(True)
        self.travel_date.setMinimumDate(QDate.currentDate())
        self.travel_date.setMaximumDate(QDate.currentDate().addDays(365))
        self.after = QTimeEdit(QTime(0, 0)); self.after.setDisplayFormat("HH:mm")
        self.before = QTimeEdit(QTime(23, 59)); self.before.setDisplayFormat("HH:mm")
        self.train_type = QComboBox(); self.train_type.addItems(["KTX", "전체 열차"])
        self.seat = QComboBox(); self.seat.addItems(["일반실 우선", "일반실만", "특실 우선", "특실만"])
        self.passengers = QSpinBox(); self.passengers.setRange(1, 9)
        self.strategy = QComboBox(); self.strategy.addItems(["연속 좌석", "개별 좌석"])
        form.addRow("출발역", self.source); form.addRow("도착역", self.destination)
        form.addRow("출발일", self.travel_date); form.addRow("시작 시간", self.after)
        form.addRow("종료 시간", self.before); form.addRow("열차", self.train_type)
        form.addRow("좌석", self.seat); form.addRow("인원", self.passengers); form.addRow("배치", self.strategy)
        layout.addWidget(search)

        buttons = QHBoxLayout()
        self.login_button = QPushButton("로그인 확인")
        self.start_button = QPushButton("예약 시작")
        self.stop_button = QPushButton("중지"); self.stop_button.setEnabled(False)
        self.payment_button = QPushButton("결제 페이지 열기")
        self.login_button.clicked.connect(lambda: self._start(login_only=True))
        self.start_button.clicked.connect(lambda: self._start(login_only=False))
        self.stop_button.clicked.connect(self._stop)
        self.payment_button.clicked.connect(lambda: webbrowser.open(settings.KORAIL_PAYMENT_URL))
        for button in (self.login_button, self.start_button, self.stop_button, self.payment_button): buttons.addWidget(button)
        layout.addLayout(buttons)

        self.status_label = QLabel("준비됨")
        self.progress_label = QLabel("조회 0회 | 최근 조회 -")
        self.log = QTextEdit(); self.log.setReadOnly(True)
        layout.addWidget(self.status_label); layout.addWidget(self.progress_label); layout.addWidget(self.log, 1)
        return page

    def _notification_tab(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page)
        group = QGroupBox("Gmail 알림"); form = QFormLayout(group)
        self.email_sender = QLineEdit(); self.email_sender.setPlaceholderText("sender@gmail.com")
        self.email_password = QLineEdit(); self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password.setPlaceholderText("Google 앱 비밀번호 16자리")
        self.email_recipient = QLineEdit(); self.email_recipient.setPlaceholderText("recipient@example.com")
        self.save_email = QCheckBox("Windows 자격 증명 관리자에 Gmail 앱 비밀번호 저장")
        self.test_email_button = QPushButton("테스트 메일 보내기")
        self.test_email_button.clicked.connect(self._test_email)
        form.addRow("발신 Gmail", self.email_sender); form.addRow("앱 비밀번호", self.email_password)
        form.addRow("수신 이메일", self.email_recipient); form.addRow("", self.save_email); form.addRow("", self.test_email_button)
        layout.addWidget(group)
        info = QLabel("Google 계정에 2단계 인증을 설정한 뒤 앱 비밀번호를 사용하세요.\n예약 성공과 치명적 오류에만 이메일을 보냅니다.")
        info.setWordWrap(True); layout.addWidget(info); layout.addStretch()
        return page

    def _request(self) -> ReservationRequest | None:
        source = self.source.currentText().strip().removesuffix("역")
        destination = self.destination.currentText().strip().removesuffix("역")
        if source not in FALLBACK_STATIONS or destination not in FALLBACK_STATIONS:
            QMessageBox.warning(self, "입력 확인", "출발역과 도착역을 목록에서 선택하세요."); return None
        if source == destination:
            QMessageBox.warning(self, "입력 확인", "출발역과 도착역은 달라야 합니다."); return None
        if not self.username.text().strip() or not self.password.text():
            QMessageBox.warning(self, "입력 확인", "코레일 계정을 입력하세요."); return None
        after = self.after.time().toString("HHmm") + "00"
        before = self.before.time().toString("HHmm")
        if before != "0000" and int(before) <= int(after[:4]):
            QMessageBox.warning(self, "입력 확인", "종료 시간은 시작 시간보다 늦어야 합니다."); return None
        options = [ReserveOption.GENERAL_FIRST, ReserveOption.GENERAL_ONLY, ReserveOption.SPECIAL_FIRST, ReserveOption.SPECIAL_ONLY]
        return ReservationRequest(
            self.username.text().strip(), self.password.text(), source, destination,
            self.travel_date.date().toString("yyyyMMdd"), after, "2400" if before == "0000" else before,
            self.passengers.value(), TrainType.KTX if self.train_type.currentIndex() == 0 else TrainType.ALL,
            options[self.seat.currentIndex()], "consecutive" if self.strategy.currentIndex() == 0 else "random",
            self.email_sender.text().strip(), self.email_password.text(), self.email_recipient.text().strip(),
        )

    def _start(self, login_only: bool) -> None:
        if self.thread and self.thread.isRunning(): return
        request = self._request()
        if not request: return
        if not login_only and QMessageBox.question(self, "예약 시작", f"{request.date} {request.source}→{request.destination} 조건으로 자동 예약을 시작할까요?") != QMessageBox.StandardButton.Yes:
            return
        self._save_settings()
        self.thread = QThread(self); self.worker = ReservationWorker(request, login_only)
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self._set_status); self.worker.progress.connect(self._progress)
        self.worker.succeeded.connect(self._success); self.worker.failed.connect(self._failure)
        self.worker.login_checked.connect(self._login_checked); self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self._finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self._set_running(True); self.thread.start()

    def _stop(self) -> None:
        if self.worker:
            self.worker.cancel(); self._set_status("중지 요청 중...")

    def _set_running(self, running: bool) -> None:
        self.login_button.setEnabled(not running); self.start_button.setEnabled(not running); self.stop_button.setEnabled(running)

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text); self.log.append(text)

    def _progress(self, attempts: int, timestamp: str) -> None:
        self.progress_label.setText(f"조회 {attempts:,}회 | 최근 조회 {timestamp}")

    def _success(self, message: str) -> None:
        self._set_status("예약 성공 - 결제가 필요합니다."); QApplication.beep(); QMessageBox.information(self, "코레일 예약 성공", message)

    def _failure(self, message: str) -> None:
        self._set_status(f"오류: {message}"); QApplication.beep(); QMessageBox.critical(self, "예약 오류", message)

    def _login_checked(self, ok: bool, message: str) -> None:
        if self.worker and self.worker.login_only:
            (QMessageBox.information if ok else QMessageBox.warning)(self, "로그인 확인", message)

    def _finished(self) -> None:
        self._set_running(False); self.worker = None; self.thread = None

    def _valid_email_settings(self) -> bool:
        values = (self.email_sender.text().strip(), self.email_password.text(), self.email_recipient.text().strip())
        if not all(values) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values[0]) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values[2]):
            QMessageBox.warning(self, "Gmail 설정", "발신 Gmail, 앱 비밀번호, 수신 이메일을 확인하세요."); return False
        return True

    def _test_email(self) -> None:
        if not self._valid_email_settings() or (self.email_thread and self.email_thread.isRunning()): return
        self.test_email_button.setEnabled(False)
        self.email_thread = EmailTestThread(
            self.email_sender.text(), self.email_password.text(), self.email_recipient.text()
        )
        self.email_thread.completed.connect(self._email_test_completed)
        self.email_thread.finished.connect(self._email_finished)
        self.email_thread.start()

    def _email_test_completed(self, ok: bool, message: str) -> None:
        if ok:
            QMessageBox.information(self, "Gmail 테스트", message)
        else:
            self.log.append(message)
            QMessageBox.warning(self, "Gmail 테스트 실패", message)

    def _email_finished(self) -> None:
        if self.email_thread:
            self.email_thread.deleteLater()
        self.email_thread = None
        self.test_email_button.setEnabled(True)

    def _load_settings(self) -> None:
        self.username.setText(self.settings.value("username", "")); self.email_sender.setText(self.settings.value("email_sender", "")); self.email_recipient.setText(self.settings.value("email_recipient", ""))
        try:
            self.password.setText(self.credentials.get("korail_password")); self.email_password.setText(self.credentials.get("gmail_app_password"))
            self.save_account.setChecked(bool(self.password.text())); self.save_email.setChecked(bool(self.email_password.text()))
        except Exception:
            self.log.append("Windows 자격 증명 관리자를 사용할 수 없습니다.")

    def _save_settings(self) -> None:
        self.settings.setValue("username", self.username.text().strip() if self.save_account.isChecked() else ""); self.settings.setValue("email_sender", self.email_sender.text().strip()); self.settings.setValue("email_recipient", self.email_recipient.text().strip())
        try:
            self.credentials.set("korail_password", self.password.text() if self.save_account.isChecked() else "")
            self.credentials.set("gmail_app_password", self.email_password.text() if self.save_email.isChecked() else "")
        except Exception:
            self.log.append("비밀번호를 Windows 자격 증명 관리자에 저장하지 못했습니다.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if (self.thread and self.thread.isRunning()) or (self.email_thread and self.email_thread.isRunning()):
            QMessageBox.warning(self, "작업 실행 중", "예약 또는 이메일 테스트가 끝난 뒤 종료하세요."); event.ignore(); return
        self._save_settings(); event.accept()
