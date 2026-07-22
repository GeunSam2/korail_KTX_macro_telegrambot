import os
import sys
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def test_windows_notification_is_default_result_channel():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.tray.showMessage = MagicMock()

    with patch("gui.main_window.QSystemTrayIcon.isSystemTrayAvailable", return_value=True):
        window._show_windows_notification("예약 성공", "결제하세요")

    window.tray.showMessage.assert_called_once()
    window.close()
    assert app is not None


def test_completion_notification_tab_has_independent_channels():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.centralWidget().tabText(1) == "완료 알림"
    assert hasattr(window, "email_recipient")
    assert hasattr(window, "enable_email")
    assert hasattr(window, "enable_telegram")
    assert hasattr(window, "enable_windows")
    assert not hasattr(window, "credentials_file")
    window.close()
    assert app is not None


def test_success_shows_both_windows_notification_and_popup(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.enable_windows.setChecked(True)
    toast = MagicMock()
    popup = MagicMock()
    monkeypatch.setattr(window, "_show_windows_notification", toast)
    monkeypatch.setattr("gui.main_window.QMessageBox.information", popup)

    window._success("예약되었습니다")

    toast.assert_called_once()
    popup.assert_called_once()
    window.close()
    assert app is not None


def test_oauth_help_contains_only_personal_setup(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    shown = MagicMock()
    monkeypatch.setattr("gui.main_window.QMessageBox.information", shown)

    window._show_oauth_help()

    message = shown.call_args.args[2]
    assert "개인 또는 개발용" in message
    assert "배포판 사용자" not in message
    window.close()
    assert app is not None


def test_distribution_oauth_client_next_to_exe_is_detected(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    executable = tmp_path / "KTX 자동예약.exe"
    client = tmp_path / "oauth_client.json"
    client.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    window = MainWindow()

    assert window._bundled_oauth_client_file() == str(client)
    window.close()
    assert app is not None


def test_station_fields_start_unselected_and_date_defaults_to_today():
    from PySide6.QtCore import QDate

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.source.currentIndex() == -1
    assert window.destination.currentIndex() == -1
    assert window.source.currentText() == ""
    assert window.destination.currentText() == ""
    assert window.travel_date.date() == QDate.currentDate()
    window.close()
    assert app is not None


def test_reservation_request_rejects_unselected_stations(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    warning = MagicMock()
    monkeypatch.setattr("gui.main_window.QMessageBox.warning", warning)

    assert window._request() is None
    warning.assert_called_once()
    window.close()
    assert app is not None
