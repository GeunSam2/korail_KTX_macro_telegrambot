import smtplib
import threading
from unittest.mock import MagicMock, patch

from services.korail_service import KorailService
from services.notification_service import GmailNotification, NotificationPipeline


def test_reservation_loop_honors_preexisting_cancel_event():
    service = KorailService()
    service._logged_in = True
    cancelled = threading.Event()
    cancelled.set()

    result = service.search_and_reserve_loop(
        "20260801", "광명", "오송", cancel_event=cancelled
    )

    assert result is None


def test_progress_callback_reports_attempt():
    service = KorailService()
    service._logged_in = True
    service._search_interval = 0
    service.search_trains = MagicMock(return_value=[])
    progress = []

    service.search_and_reserve_loop(
        "20260801", "광명", "오송", max_attempts=1,
        progress_callback=progress.append,
    )

    assert progress[0]["attempts"] == 1


def test_gmail_notification_success():
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("smtplib.SMTP_SSL", return_value=smtp):
        assert GmailNotification("from@gmail.com", "abcd efgh", "to@example.com").send("title", "body")
    smtp.login.assert_called_once_with("from@gmail.com", "abcdefgh")
    smtp.send_message.assert_called_once()


def test_gmail_detailed_authentication_failure():
    error = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
    with patch("smtplib.SMTP_SSL", side_effect=error):
        ok, detail = GmailNotification("from@gmail.com", "secret", "to@example.com").send_detailed("title", "body")
    assert not ok
    assert "16자리" in detail


def test_gmail_notification_failure_is_nonfatal():
    with patch("smtplib.SMTP_SSL", side_effect=OSError("offline")):
        assert not GmailNotification("from@gmail.com", "secret", "to@example.com").send("title", "body")


def test_pipeline_isolates_broken_channel():
    broken = MagicMock()
    broken.send.side_effect = RuntimeError("broken")
    working = MagicMock()
    working.send.return_value = True
    assert NotificationPipeline([broken, working]).send("title", "body") == [False, True]
