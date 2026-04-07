"""Payment reminder service."""
import time
import requests
from datetime import datetime

from config.settings import settings
from models import PaymentStatus
from storage.base import StorageInterface
from services.telegram_service import TelegramService, MessageTemplates
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
        Start sending payment reminders to a user.

        Sends reminders at configured intervals until:
        - User confirms payment
        - Timeout expires

        Args:
            chat_id: Telegram chat ID to send reminders to
        """
        # Initialize payment status
        payment_status = PaymentStatus(
            chat_id=chat_id,
            completed=False,
            reservation_time=datetime.now(),
            reminder_active=True
        )
        self.storage.save_payment_status(payment_status)

        total_seconds = self.timeout_minutes * 60
        logger.info(
            f"Starting payment reminders for chat_id={chat_id}, "
            f"timeout={self.timeout_minutes}min, interval={self.interval_seconds}sec"
        )

        for elapsed in range(self.interval_seconds, total_seconds + self.interval_seconds, self.interval_seconds):
            time.sleep(self.interval_seconds)

            # Check if payment completed
            if self.check_payment_completed(chat_id):
                self._send_completion_message(chat_id)
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
        """Send payment completion confirmation."""
        message = """
✅ 결제 완료 확인!
결제를 완료하셨습니다.
즐거운 여행 되세요! 🚄
"""
        self.telegram.send_message(chat_id, message)
        logger.info(f"Sent payment completion message to chat_id={chat_id}")

    def _send_timeout_message(self, chat_id: int) -> None:
        """Send timeout warning message."""
        message = """
⚠️ 예약 시간 만료 ⚠️
예약 제한 시간 10분이 경과했습니다.
결제를 완료하지 않으셨다면 예약이 취소되었을 수 있습니다.

사이트에서 예약 상태를 확인해주세요.
"""
        self.telegram.send_message(chat_id, message)
        logger.warning(f"Payment timeout for chat_id={chat_id}")
