import os
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


def test_email_tab_requires_explicit_user_configuration():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.centralWidget().tabText(1) == "이메일 알림"
    assert hasattr(window, "email_recipient")
    assert not hasattr(window, "credentials_file")
    window.close()
    assert app is not None
