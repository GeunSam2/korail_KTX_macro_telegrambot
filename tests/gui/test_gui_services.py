import smtplib
import json
import threading
from unittest.mock import MagicMock, patch

from gui.worker import EmailTestThread
from services.korail_service import KorailService
from services.google_oauth_service import GoogleOAuthNotification
from services.notification_service import GmailNotification, NotificationPipeline, TelegramNotification


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


def test_telegram_notification_success():
    response = MagicMock()
    response.json.return_value = {"ok": True}
    with patch("services.notification_service.requests.post", return_value=response) as post:
        assert TelegramNotification("token", "1234").send("title", "body")
    post.assert_called_once()


def test_email_thread_converts_unexpected_exception_to_failure_signal():
    thread = EmailTestThread("{}", "to@example.com")
    thread.channel.send_detailed = MagicMock(side_effect=RuntimeError("unexpected"))
    results = []
    thread.completed.connect(lambda ok, message: results.append((ok, message)))

    thread.run()

    assert results == [(False, "이메일 테스트 오류: RuntimeError: unexpected")]


def test_google_oauth_notification_sends_to_connected_account():
    credentials = MagicMock(valid=True, expired=False)
    send_call = MagicMock()
    send_call.execute.return_value = {"id": "message-id"}
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value = send_call
    with patch("services.google_oauth_service.Credentials.from_authorized_user_info", return_value=credentials), patch(
        "services.google_oauth_service.build", return_value=service
    ):
        ok, detail = GoogleOAuthNotification('{"token":"test"}', "self@gmail.com").send_detailed("title", "body")
    assert ok
    assert detail == "발송 성공"
    service.users.return_value.messages.return_value.send.assert_called_once()


def test_google_oauth_reports_disabled_gmail_api():
    from googleapiclient.errors import HttpError

    credentials = MagicMock(valid=True, expired=False)
    response = MagicMock(status=403, reason="Forbidden")
    content = json.dumps({"error": {"message": "Gmail API has not been used or is disabled", "status": "PERMISSION_DENIED"}}).encode()
    send_call = MagicMock()
    send_call.execute.side_effect = HttpError(response, content)
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value = send_call
    with patch("services.google_oauth_service.Credentials.from_authorized_user_info", return_value=credentials), patch(
        "services.google_oauth_service.build", return_value=service
    ):
        ok, detail = GoogleOAuthNotification('{"token":"test"}', "to@example.com").send_detailed("title", "body")
    assert not ok
    assert "Gmail API가 활성화되지 않았습니다" in detail
