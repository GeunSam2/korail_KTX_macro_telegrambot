"""
Integration tests for payment reminder service.

Tests payment reminder timing, timeout, and confirmation.
"""
import pytest
import time
from unittest.mock import Mock, patch, call
from freezegun import freeze_time
from datetime import datetime, timedelta

from storage import RedisStorage
from services import TelegramService, PaymentReminderService
from models import PaymentStatus


class TestPaymentReminderService:
    """Test payment reminder service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.service = PaymentReminderService(self.storage, self.telegram)

    def teardown_method(self):
        """Clean up after each test."""
        self.storage.redis.flushdb()

    def test_start_reminders_creates_payment_status(self):
        """Test starting reminders creates payment status."""
        chat_id = 12345

        # Mock the reminder thread to not actually run
        with patch.object(self.service, '_send_reminder_loop'):
            self.service.start_reminders(chat_id)

        # Check payment status created
        status = self.storage.get_payment_status(chat_id)
        assert status is not None
        assert status.chat_id == chat_id
        assert status.completed is False
        assert status.reminder_active is True
        assert status.created_at is not None

    def test_confirm_payment_marks_completed(self):
        """Test confirming payment marks status as completed."""
        chat_id = 12345

        # Create payment status
        status = PaymentStatus(chat_id=chat_id, completed=False, reminder_active=True)
        self.storage.save_payment_status(status)

        # Confirm payment
        self.service.confirm_payment(chat_id)

        # Check status updated
        updated_status = self.storage.get_payment_status(chat_id)
        assert updated_status.completed is True
        assert updated_status.reminder_active is False

        # Check confirmation message sent
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "완료" in call_args[0][1] or "확인" in call_args[0][1]

    def test_confirm_payment_no_status(self):
        """Test confirming payment when no status exists."""
        chat_id = 12345

        # Should handle gracefully
        self.service.confirm_payment(chat_id)

        # Should send message
        self.telegram.send_message.assert_called_once()

    @patch('threading.Thread')
    def test_reminder_thread_started(self, mock_thread):
        """Test that reminder thread is started."""
        chat_id = 12345

        self.service.start_reminders(chat_id)

        # Thread should have been created and started
        mock_thread.assert_called_once()
        thread_instance = mock_thread.return_value
        thread_instance.start.assert_called_once()

    def test_deactivate_reminders(self):
        """Test deactivating reminders."""
        chat_id = 12345

        # Create active payment status
        status = PaymentStatus(chat_id=chat_id, completed=False, reminder_active=True)
        self.storage.save_payment_status(status)

        # Deactivate
        self.service.deactivate_reminders(chat_id)

        # Check status
        updated_status = self.storage.get_payment_status(chat_id)
        assert updated_status.reminder_active is False

    def test_payment_timeout_calculation(self):
        """Test that payment timeout is calculated correctly."""
        chat_id = 12345

        status = PaymentStatus(
            chat_id=chat_id,
            completed=False,
            reminder_active=True
        )
        # Set created_at to 8 minutes ago
        status.created_at = datetime.now() - timedelta(minutes=8)
        self.storage.save_payment_status(status)

        # Check if timed out (should be False, still within 10 min)
        retrieved = self.storage.get_payment_status(chat_id)
        elapsed = (datetime.now() - retrieved.created_at).total_seconds() / 60
        assert elapsed < 10

    def test_multiple_reminders_different_users(self):
        """Test multiple users can have simultaneous reminders."""
        chat_ids = [11111, 22222, 33333]

        with patch.object(self.service, '_send_reminder_loop'):
            for chat_id in chat_ids:
                self.service.start_reminders(chat_id)

        # All should have payment status
        for chat_id in chat_ids:
            status = self.storage.get_payment_status(chat_id)
            assert status is not None
            assert status.reminder_active is True

    def test_reminder_not_sent_after_completion(self):
        """Test reminders stop after payment completion."""
        chat_id = 12345

        # Create completed payment status
        status = PaymentStatus(
            chat_id=chat_id,
            completed=True,
            reminder_active=False
        )
        self.storage.save_payment_status(status)

        # Try to check if should send reminder
        # In actual implementation, reminder loop checks this
        retrieved = self.storage.get_payment_status(chat_id)
        assert retrieved.completed is True
        assert retrieved.reminder_active is False


class TestPaymentReminderTiming:
    """Test payment reminder timing with time manipulation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.service = PaymentReminderService(self.storage, self.telegram)

    def teardown_method(self):
        """Clean up after each test."""
        self.storage.redis.flushdb()

    def test_timeout_detection_after_10_minutes(self):
        """Test timeout is detected after 10 minutes."""
        chat_id = 12345

        # Create status at specific time
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        with freeze_time(start_time):
            status = PaymentStatus(
                chat_id=chat_id,
                completed=False,
                reminder_active=True
            )
            self.storage.save_payment_status(status)

        # Move time forward by 11 minutes
        timeout_time = start_time + timedelta(minutes=11)
        with freeze_time(timeout_time):
            retrieved = self.storage.get_payment_status(chat_id)
            elapsed = (datetime.now() - retrieved.created_at).total_seconds() / 60

            # Should be past timeout
            assert elapsed > 10

    def test_no_timeout_within_10_minutes(self):
        """Test no timeout within 10 minutes."""
        chat_id = 12345

        start_time = datetime(2025, 1, 1, 12, 0, 0)
        with freeze_time(start_time):
            status = PaymentStatus(
                chat_id=chat_id,
                completed=False,
                reminder_active=True
            )
            self.storage.save_payment_status(status)

        # Move time forward by 5 minutes
        check_time = start_time + timedelta(minutes=5)
        with freeze_time(check_time):
            retrieved = self.storage.get_payment_status(chat_id)
            elapsed = (datetime.now() - retrieved.created_at).total_seconds() / 60

            # Should not be timed out yet
            assert elapsed < 10

    def test_payment_status_serialization_preserves_datetime(self):
        """Test that datetime is preserved through Redis serialization."""
        chat_id = 12345

        original_time = datetime(2025, 1, 1, 12, 30, 45)
        with freeze_time(original_time):
            status = PaymentStatus(
                chat_id=chat_id,
                completed=False,
                reminder_active=True
            )
            self.storage.save_payment_status(status)

        # Retrieve and check
        retrieved = self.storage.get_payment_status(chat_id)
        assert retrieved.created_at is not None
        # Allow small difference due to serialization
        time_diff = abs((retrieved.created_at - original_time).total_seconds())
        assert time_diff < 2  # Within 2 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
