"""Main desktop window for non-technical Korail users."""
from __future__ import annotations

import webbrowser
from datetime import date, timedelta

from PySide6.QtCore import QDate, QSettings, QThread, QTime, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QFormLayout, QGroupBox,
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)
from korail2 import ReserveOption, TrainType

from config.settings import settings
from gui.worker import EmailTestThread, GoogleLoginThread, ReservationRequest, ReservationWorker
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
        self.google_login_thread: GoogleLoginThread | None = None
        self.google_token = ""
        self.google_email = ""
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
        group = QGroupBox("Google Gmail 알림"); form = QFormLayout(group)
        self.oauth_status = QLabel("Google 로그인 필요")
        self.google_login_button = QPushButton("Google 로그인")
        self.google_login_button.clicked.connect(self._google_login)
        self.google_setup_button = QPushButton("Google OAuth 설정 페이지")
        self.google_setup_button.clicked.connect(
            lambda: webbrowser.open("https://console.cloud.google.com/apis/credentials")
        )
        self.google_disconnect_button = QPushButton("Google 연결 해제")
        self.google_disconnect_button.clicked.connect(self._google_disconnect)
        self.email_recipient = QLineEdit(); self.email_recipient.setPlaceholderText("recipient@example.com")
        self.test_email_button = QPushButton("테스트 메일 보내기")
        self.test_email_button.clicked.connect(self._test_email)
        form.addRow("연동 상태", self.oauth_status)
        oauth_buttons = QHBoxLayout(); oauth_buttons.addWidget(self.google_setup_button); oauth_buttons.addWidget(self.google_login_button); oauth_buttons.addWidget(self.google_disconnect_button)
        form.addRow("", oauth_buttons)
        form.addRow("수신 이메일", self.email_recipient)
        form.addRow("", self.test_email_button)
        layout.addWidget(group)
        info = QLabel("Google 로그인 버튼을 누르면 기본 브라우저에서 계정 선택과 Gmail 발송 권한 승인을 진행합니다.\n앱은 Google 비밀번호를 읽거나 저장하지 않습니다.")
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
            email_recipient=self.email_recipient.text().strip(), google_token=self.google_token,
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
        import re
        recipient = self.email_recipient.text().strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
            QMessageBox.warning(self, "Gmail 설정", "올바른 수신 이메일 주소를 입력하세요.")
            return False
        if not self.google_token or not self.google_email:
            QMessageBox.warning(self, "Google 로그인 필요", "먼저 Google 로그인 버튼을 눌러 Gmail을 연동하세요."); return False
        return True

    def _test_email(self) -> None:
        if not self._valid_email_settings() or (self.email_thread and self.email_thread.isRunning()): return
        self.test_email_button.setEnabled(False)
        self.email_thread = EmailTestThread(self.google_token, self.email_recipient.text().strip())
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

    def _google_login(self) -> None:
        if self.google_login_thread and self.google_login_thread.isRunning():
            return
        client_file = self.settings.value("google_oauth_client_file", "")
        from pathlib import Path
        if not client_file or not Path(client_file).is_file():
            QMessageBox.information(
                self,
                "Google OAuth 설정 파일",
                "Google Cloud에서 Gmail API를 활성화하고 '데스크톱 앱' OAuth 클라이언트 JSON을 다운로드한 뒤 선택하세요.",
            )
            client_file, _ = QFileDialog.getOpenFileName(self, "Google OAuth JSON 선택", "", "JSON 파일 (*.json)")
            if not client_file:
                return
            self.settings.setValue("google_oauth_client_file", client_file)
        self.google_login_button.setEnabled(False)
        self.oauth_status.setText("브라우저에서 Google 로그인 중...")
        self.google_login_thread = GoogleLoginThread(client_file)
        self.google_login_thread.completed.connect(self._google_login_completed)
        self.google_login_thread.finished.connect(self._google_login_finished)
        self.google_login_thread.start()

    def _google_login_completed(self, ok: bool, token: str, email: str, message: str) -> None:
        if ok:
            self.google_token = token
            self.google_email = email
            self.credentials.set("google_oauth_token", token)
            self.settings.setValue("google_account_email", email)
            self.oauth_status.setText(f"Google Gmail 연동됨: {email}")
            QMessageBox.information(self, "Google 로그인", message)
        else:
            self.oauth_status.setText("Google 로그인 실패")
            self.log.append(message)
            QMessageBox.warning(self, "Google 로그인 실패", message)

    def _google_login_finished(self) -> None:
        if self.google_login_thread:
            self.google_login_thread.deleteLater()
        self.google_login_thread = None
        self.google_login_button.setEnabled(True)

    def _google_disconnect(self) -> None:
        self.credentials.delete("google_oauth_token")
        self.google_token = ""
        self.google_email = ""
        self.settings.remove("google_account_email")
        self.oauth_status.setText("Google 로그인 필요")
        QMessageBox.information(self, "Google 연결 해제", "이 앱에 저장된 Google 인증 토큰을 삭제했습니다.")

    def _load_settings(self) -> None:
        self.username.setText(self.settings.value("username", ""))
        self.email_recipient.setText(self.settings.value("email_recipient", ""))
        try:
            self.credentials.delete("gmail_app_password")
            self.password.setText(self.credentials.get("korail_password")); self.google_token = self.credentials.get("google_oauth_token")
            self.google_email = self.settings.value("google_account_email", "")
            self.save_account.setChecked(bool(self.password.text()))
            self.oauth_status.setText(f"Google Gmail 연동됨: {self.google_email}" if self.google_token and self.google_email else "Google 로그인 필요")
        except Exception:
            self.log.append("Windows 자격 증명 관리자를 사용할 수 없습니다.")

    def _save_settings(self) -> None:
        self.settings.setValue("username", self.username.text().strip() if self.save_account.isChecked() else "")
        self.settings.setValue("email_recipient", self.email_recipient.text().strip())
        try:
            self.credentials.set("korail_password", self.password.text() if self.save_account.isChecked() else "")
        except Exception:
            self.log.append("비밀번호를 Windows 자격 증명 관리자에 저장하지 못했습니다.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if ((self.thread and self.thread.isRunning()) or (self.email_thread and self.email_thread.isRunning())
                or (self.google_login_thread and self.google_login_thread.isRunning())):
            QMessageBox.warning(self, "작업 실행 중", "예약 또는 이메일 테스트가 끝난 뒤 종료하세요."); event.ignore(); return
        self._save_settings(); event.accept()
