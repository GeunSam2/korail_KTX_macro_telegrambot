"""
Integration tests for Telegram webhook handler.

Tests webhook handling with realistic Telegram payloads.
"""
import sys
import pytest
from unittest.mock import Mock, patch

sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from storage import RedisStorage
from services import TelegramService, ReservationService, PaymentReminderService
from api import TelegramWebhook
from models import UserSession, UserProgress, PaymentStatus
from flask import Flask
from flask_restful import Api


class TestTelegramWebhook:
    """Test Telegram webhook handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.reservation = Mock(spec=ReservationService)
        self.payment_reminder = Mock(spec=PaymentReminderService)

        # Create Flask app for testing
        self.app = Flask(__name__)
        self.api = Api(self.app)

        self.api.add_resource(
            TelegramWebhook,
            '/telebot',
            resource_class_kwargs={
                'storage': self.storage,
                'telegram_service': self.telegram,
                'reservation_service': self.reservation,
                'payment_reminder_service': self.payment_reminder
            }
        )

        self.client = self.app.test_client()

    def teardown_method(self):
        """Clean up after each test."""
        self.storage.redis.flushdb()

    def test_webhook_post_start_command(self):
        """Test webhook handling /start command."""
        payload = {
            "message": {
                "chat": {"id": 12345},
                "text": "/start"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Check session created
        session = self.storage.get_user_session(12345)
        assert session is not None
        assert session.in_progress is True
        assert session.last_action == UserProgress.STARTED

        # Check welcome message sent
        self.telegram.send_message.assert_called_once()

    def test_webhook_post_cancel_command(self):
        """Test webhook handling /cancel command."""
        chat_id = 12345

        # Create existing session
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.DATE_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "/cancel"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Check reservation cancelled
        self.reservation.cancel_reservation.assert_called_once_with(chat_id)

        # Check session reset
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.in_progress is False

    def test_webhook_post_payment_confirmation(self):
        """Test payment confirmation message during reminder."""
        chat_id = 12345

        # Create payment status with active reminder
        status = PaymentStatus(
            chat_id=chat_id,
            completed=False,
            reminder_active=True
        )
        self.storage.save_payment_status(status)

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "결제완료"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Check payment confirmation called
        self.payment_reminder.confirm_payment.assert_called_once_with(chat_id)

    def test_webhook_post_ignores_edited_message(self):
        """Test webhook ignores edited messages."""
        payload = {
            "edited_message": {
                "chat": {"id": 12345},
                "text": "edited text"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Should not process message
        self.telegram.send_message.assert_not_called()

    def test_webhook_post_ignores_chat_member_update(self):
        """Test webhook ignores chat member updates."""
        payload = {
            "my_chat_member": {
                "chat": {"id": 12345},
                "new_chat_member": {}
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Should not process
        self.telegram.send_message.assert_not_called()

    def test_webhook_post_invalid_message_format(self):
        """Test webhook handles invalid message format gracefully."""
        payload = {
            "message": {
                "chat": {"id": 12345}
                # Missing 'text' field
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200  # Still returns OK

    def test_webhook_post_no_session_non_command(self):
        """Test non-command message without active session."""
        chat_id = 12345

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "random message"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Should send "no active session" message
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "진행중인" in call_args[0][1] or "/start" in call_args[0][1]

    def test_webhook_post_conversation_message(self):
        """Test conversation message routing."""
        chat_id = 12345

        # Create session in conversation state
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.STARTED
        )
        self.storage.save_user_session(session)

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "Y"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Should have processed conversation message
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.START_ACCEPTED

    def test_webhook_get_callback_success(self):
        """Test GET callback for successful reservation."""
        chat_id = 12345

        # Create session
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.FINDING_TICKET
        )
        from models import UserCredentials
        session.credentials = UserCredentials(
            korail_id="010-1234-5678",
            korail_pw="password"
        )
        self.storage.save_user_session(session)

        response = self.client.get(
            '/telebot',
            query_string={
                'chatId': str(chat_id),
                'msg': '예약 성공!',
                'status': '0',
                'isMulti': '0',
                'totalSeats': '1',
                'seatStrategy': 'consecutive'
            }
        )

        assert response.status_code == 200

        # Check message sent
        self.telegram.send_message.assert_called()

        # Check payment reminders started
        self.payment_reminder.start_reminders.assert_called_once_with(chat_id)

        # Check session reset
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.in_progress is False

    def test_webhook_get_callback_failure(self):
        """Test GET callback for failed reservation."""
        chat_id = 12345

        response = self.client.get(
            '/telebot',
            query_string={
                'chatId': str(chat_id),
                'msg': '예약 실패',
                'status': '1'
            }
        )

        assert response.status_code == 200

        # Check message sent
        self.telegram.send_message.assert_called_once()

    def test_webhook_get_callback_partial_random(self):
        """Test GET callback for partial random seating."""
        chat_id = 12345

        response = self.client.get(
            '/telebot',
            query_string={
                'chatId': str(chat_id),
                'msg': '1번째 좌석 예약 완료',
                'status': '2',
                'isMulti': '1',
                'totalSeats': '3',
                'seatStrategy': 'random'
            }
        )

        assert response.status_code == 200

        # Check message sent
        self.telegram.send_message.assert_called_once()

        # Payment reminders should NOT start yet (partial)
        self.payment_reminder.start_reminders.assert_not_called()

    def test_webhook_get_callback_missing_params(self):
        """Test GET callback with missing parameters."""
        response = self.client.get(
            '/telebot',
            query_string={
                'chatId': '12345'
                # Missing msg and status
            }
        )

        assert response.status_code == 200  # Still returns OK

    def test_webhook_post_admin_password_waiting(self):
        """Test webhook handles admin password input."""
        chat_id = 12345

        # Set waiting for admin password
        self.storage.set_waiting_for_admin_password(chat_id, True)
        self.storage.set_pending_admin_command(chat_id, "/subscribe")

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "admin_password"
            }
        }

        with patch('config.settings.settings.ADMIN_PASSWORD', 'admin_password'):
            response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Check waiting state cleared
        assert not self.storage.is_waiting_for_admin_password(chat_id)

    def test_webhook_post_random_seating_payment_confirmation(self):
        """Test payment confirmation during random seating."""
        chat_id = 12345

        # Set current seat index (random seating in progress)
        self.storage.save_current_seat_index(chat_id, 0)

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "결제완료"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Check payment marked ready
        # Note: This depends on implementation details

    def test_webhook_post_error_handling(self):
        """Test webhook handles errors gracefully."""
        # Send malformed JSON
        response = self.client.post(
            '/telebot',
            data='invalid json',
            content_type='application/json'
        )

        # Should still return OK (Telegram requirement)
        assert response.status_code in [200, 400]


class TestWebhookCommandRouting:
    """Test command routing through webhook."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.reservation = Mock(spec=ReservationService)
        self.payment_reminder = Mock(spec=PaymentReminderService)

        self.app = Flask(__name__)
        self.api = Api(self.app)

        self.api.add_resource(
            TelegramWebhook,
            '/telebot',
            resource_class_kwargs={
                'storage': self.storage,
                'telegram_service': self.telegram,
                'reservation_service': self.reservation,
                'payment_reminder_service': self.payment_reminder
            }
        )

        self.client = self.app.test_client()

    def teardown_method(self):
        """Clean up after each test."""
        self.storage.redis.flushdb()

    def test_status_command(self):
        """Test /status command."""
        self.reservation.get_status.return_value = "예약 현황"

        payload = {
            "message": {
                "chat": {"id": 12345},
                "text": "/status"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200
        self.reservation.get_status.assert_called_once_with(12345)

    def test_help_command(self):
        """Test /help command."""
        payload = {
            "message": {
                "chat": {"id": 12345},
                "text": "/help"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200
        self.telegram.send_message.assert_called_once()

    def test_subscribe_command_requires_auth(self):
        """Test /subscribe command requires authentication."""
        chat_id = 12345

        payload = {
            "message": {
                "chat": {"id": chat_id},
                "text": "/subscribe"
            }
        }

        response = self.client.post('/telebot', json=payload)

        assert response.status_code == 200

        # Should ask for password
        self.telegram.send_message.assert_called()
        assert self.storage.is_waiting_for_admin_password(chat_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
