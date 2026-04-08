"""Payment reminder service."""
import time
import requests
import threading
from datetime import datetime

from config.settings import settings
from models import PaymentStatus
from storage.base import StorageInterface
from services.telegram_service import TelegramService, MessageTemplates
from telegramBot.messages import Messages
from utils.logger import get_logger

logger = get_logger(__name__)


class PaymentReminderService:
    """
    Service for sending payment reminder notifications.

    Sends periodic reminders to users to complete payment within the time limit.
    """

    def __init__(
        self,
        storage: StorageInterface,
        telegram_service: TelegramService
    ):
        """
        Initialize payment reminder service.

        Args:
            storage: Storage interface for tracking payment status
            telegram_service: Telegram service for sending reminders
        """
        self.storage = storage
        self.telegram = telegram_service
        self.timeout_minutes = settings.PAYMENT_TIMEOUT_MINUTES
        self.interval_seconds = settings.PAYMENT_REMINDER_INTERVAL_SECONDS

    def start_reminders(self, chat_id: int) -> None:
        """
        Start sending payment reminders to a user (in background thread).

        Sends reminders at configured intervals until:
        - User confirms payment
        - Timeout expires

        Args:
            chat_id: Telegram chat ID to send reminders to
        """
        # Check if there's already an active reminder
        existing_status = self.storage.get_payment_status(chat_id)
        if existing_status and existing_status.reminder_active:
            logger.warning(
                f"Reminder already active for chat_id={chat_id}, skipping duplicate"
            )
            return

        # Initialize payment status
        payment_status = PaymentStatus(
            chat_id=chat_id,
            completed=False,
            reservation_time=datetime.now(),
            reminder_active=True
        )
        self.storage.save_payment_status(payment_status)

        logger.info(
            f"Starting payment reminders for chat_id={chat_id} in background thread, "
            f"timeout={self.timeout_minutes}min, interval={self.interval_seconds}sec"
        )

        # Start reminder loop in background thread (non-blocking)
        thread = threading.Thread(
            target=self._reminder_loop,
            args=(chat_id,),
            daemon=True
        )
        thread.start()

    def _reminder_loop(self, chat_id: int) -> None:
        """
        Reminder loop that runs in background thread.

        Args:
            chat_id: Telegram chat ID
        """
        try:
            total_seconds = self.timeout_minutes * 60

            for elapsed in range(self.interval_seconds, total_seconds + self.interval_seconds, self.interval_seconds):
                time.sleep(self.interval_seconds)

                # Check if payment completed
                if self.check_payment_completed(chat_id):
                    self._send_completion_message(chat_id)
                    self._deactivate_reminder(chat_id)
                    return

                # Calculate remaining time
                remaining_seconds = total_seconds - elapsed

                # Send reminder if time remaining
                if remaining_seconds > 0:
                    remaining_minutes = remaining_seconds // 60
                    remaining_secs = remaining_seconds % 60
                    self._send_reminder(chat_id, remaining_minutes, remaining_secs)

            # Final check after timeout
            if self.check_payment_completed(chat_id):
                self._send_completion_message(chat_id)
            else:
                self._send_timeout_message(chat_id)

            # Deactivate reminder after completion or timeout
            self._deactivate_reminder(chat_id)

        except Exception as e:
            logger.error(f"Error in reminder loop for chat_id={chat_id}: {e}", exc_info=True)

    def check_payment_completed(self, chat_id: int) -> bool:
        """
        Check if payment has been completed for a chat ID.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if payment completed, False otherwise
        """
        try:
            # Try internal storage first
            payment_status = self.storage.get_payment_status(chat_id)
            if payment_status and payment_status.completed:
                return True

            # Also check via API (for compatibility)
            callback_url = f"{settings.CALLBACK_BASE_URL}/check_payment"
            params = {"chatId": chat_id}
            response = requests.get(callback_url, params=params, verify=False, timeout=5)
            return response.json().get('completed', False)

        except Exception as e:
            logger.error(f"Error checking payment status for chat_id={chat_id}: {e}")
            return False

    def confirm_payment(self, chat_id: int) -> None:
        """
        Mark payment as confirmed for a chat ID.

        Args:
            chat_id: Telegram chat ID
        """
        payment_status = self.storage.get_payment_status(chat_id)
        if payment_status:
            payment_status.completed = True
            payment_status.reminder_active = False
            self.storage.save_payment_status(payment_status)
            logger.info(f"Payment confirmed for chat_id={chat_id}")
        else:
            # Create new status if not exists
            payment_status = PaymentStatus(
                chat_id=chat_id,
                completed=True,
                reminder_active=False
            )
            self.storage.save_payment_status(payment_status)

    def _send_reminder(self, chat_id: int, minutes: int, seconds: int) -> None:
        """Send a payment reminder message."""
        message = MessageTemplates.payment_reminder(minutes, seconds)
        self.telegram.send_message(chat_id, message)
        logger.debug(f"Sent payment reminder to chat_id={chat_id}, remaining={minutes}m {seconds}s")

    def _send_completion_message(self, chat_id: int) -> None:
        """Send reminder stopped message (user sent a message)."""
        self.telegram.send_message(chat_id, Messages.PAYMENT_REMINDER_STOPPED)
        logger.info(f"Sent reminder stopped message to chat_id={chat_id}")

    def _send_timeout_message(self, chat_id: int) -> None:
        """Send reminder timeout message (10 minutes elapsed)."""
        self.telegram.send_message(chat_id, Messages.PAYMENT_REMINDER_TIMEOUT)
        logger.warning(f"Payment reminder timeout for chat_id={chat_id}")

    def _deactivate_reminder(self, chat_id: int) -> None:
        """Deactivate reminder for a chat ID."""
        payment_status = self.storage.get_payment_status(chat_id)
        if payment_status:
            payment_status.reminder_active = False
            self.storage.save_payment_status(payment_status)
            logger.info(f"Deactivated reminder for chat_id={chat_id}")
