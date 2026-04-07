"""Multi-reservation payment reminder service with smart display logic."""
import threading
import time
from typing import Optional

from config.settings import settings
from models import MultiReservationStatus, SingleReservationInfo, ReservationPaymentStatus
from storage.base import StorageInterface
from services.telegram_service import TelegramService
from utils.logger import get_logger

logger = get_logger(__name__)


class MultiReservationReminderService:
    """
    Service for managing payment reminders for multiple reservations.

    Features:
    - Individual seat tracking with separate timers
    - Conditional display (only show pending seats)
    - Manual vs automatic termination distinction
    - Priority indicator for most urgent seat
    """

    def __init__(self, storage: StorageInterface, telegram: TelegramService):
        """Initialize the reminder service."""
        self.storage = storage
        self.telegram = telegram
        self.reminder_threads = {}  # chat_id -> threading.Thread
        self.interval = settings.PAYMENT_REMINDER_INTERVAL_SECONDS

    def start_reminders(self, chat_id: int) -> None:
        """
        Start sending payment reminders for multi-reservation.

        Args:
            chat_id: User's chat ID
        """
        # Check if status exists
        status = self.storage.get_multi_reservation_status(chat_id)
        if not status:
            logger.warning(f"No multi-reservation status found for chat_id={chat_id}")
            return

        # Check if reminder already running
        if chat_id in self.reminder_threads and self.reminder_threads[chat_id].is_alive():
            logger.info(f"Reminder already running for chat_id={chat_id}")
            return

        logger.info(f"Starting multi-reservation reminders for chat_id={chat_id}")

        # Start background thread
        thread = threading.Thread(
            target=self._reminder_loop,
            args=(chat_id,),
            daemon=True
        )
        thread.start()
        self.reminder_threads[chat_id] = thread

    def stop_reminders(self, chat_id: int, manual: bool = True) -> None:
        """
        Stop sending payment reminders.

        Args:
            chat_id: User's chat ID
            manual: True if manually stopped by user, False if timeout
        """
        status = self.storage.get_multi_reservation_status(chat_id)
        if not status:
            logger.warning(f"No multi-reservation status found for chat_id={chat_id}")
            return

        if manual:
            status.manually_stopped = True
            self.storage.save_multi_reservation_status(status)
            logger.info(f"Manually stopped reminders for chat_id={chat_id}")
        else:
            logger.info(f"Reminders stopped by timeout for chat_id={chat_id}")

    def _reminder_loop(self, chat_id: int) -> None:
        """
        Main reminder loop that runs in background thread.

        Args:
            chat_id: User's chat ID
        """
        try:
            while True:
                # Get current status
                status = self.storage.get_multi_reservation_status(chat_id)
                if not status:
                    logger.info(f"Status deleted, stopping reminders for chat_id={chat_id}")
                    break

                # Check if should show reminder
                if not status.should_show_reminder():
                    # Determine why we're stopping
                    if status.manually_stopped:
                        logger.info(f"Manually stopped by user, ending reminders for chat_id={chat_id}")
                    else:
                        logger.info(f"No pending reservations left, ending reminders for chat_id={chat_id}")
                    break

                # Update expired status for all reservations
                self._update_expired_reservations(status)

                # Generate and send reminder message
                message = self._generate_reminder_message(status)
                self.telegram.send_message(chat_id, message)

                # Wait before next reminder
                time.sleep(self.interval)

        except Exception as e:
            logger.error(f"Error in reminder loop for chat_id={chat_id}: {e}", exc_info=True)

    def _update_expired_reservations(self, status: MultiReservationStatus) -> None:
        """
        Update status of expired reservations.

        Args:
            status: MultiReservationStatus to update
        """
        updated = False
        for reservation in status.reservations:
            if reservation.status == ReservationPaymentStatus.PENDING and reservation.is_expired():
                reservation.status = ReservationPaymentStatus.EXPIRED
                updated = True
                logger.info(
                    f"Reservation expired: seat {reservation.seat_number} "
                    f"for chat_id={status.chat_id}"
                )

        if updated:
            self.storage.save_multi_reservation_status(status)

    def _generate_reminder_message(self, status: MultiReservationStatus) -> str:
        """
        Generate reminder message based on current status.

        Args:
            status: Current multi-reservation status

        Returns:
            Formatted reminder message
        """
        lines = ["⏰ 결제 알림\n"]
        lines.append("━━━━━━━━━━━━━━━━━━━━")

        # Get most urgent reservation
        most_urgent = status.get_most_urgent_reservation()

        # Show each reservation status
        for reservation in sorted(status.reservations, key=lambda r: r.seat_number):
            seat_num = reservation.seat_number

            if reservation.status == ReservationPaymentStatus.PENDING:
                if reservation.is_expired():
                    # Should have been marked as expired by _update_expired_reservations
                    # but show as expired anyway
                    lines.append(f"좌석 {seat_num}: ❌ 시간 만료")
                else:
                    remaining = reservation.get_remaining_minutes_display()

                    # Add priority indicator for most urgent
                    if most_urgent and reservation.seat_number == most_urgent.seat_number:
                        lines.append(f"좌석 {seat_num}: ⚠️ 가장 급함! (남은 시간: {remaining})")
                        lines.append(f"    → 먼저 결제하세요!")
                    else:
                        lines.append(f"좌석 {seat_num}: ⏳ 대기 중 (남은 시간: {remaining})")

            elif reservation.status == ReservationPaymentStatus.PAID:
                lines.append(f"좌석 {seat_num}: ✅ 결제 완료")

            elif reservation.status == ReservationPaymentStatus.EXPIRED:
                lines.append(f"좌석 {seat_num}: ❌ 시간 만료")

            elif reservation.status == ReservationPaymentStatus.CANCELLED:
                lines.append(f"좌석 {seat_num}: 🚫 취소됨")

        lines.append("━━━━━━━━━━━━━━━━━━━━")

        # Summary
        pending_count = status.get_pending_count()
        paid_count = status.get_paid_count()
        expired_count = status.get_expired_count()

        lines.append(f"\n📊 현황: 대기 {pending_count}개 | 완료 {paid_count}개 | 만료 {expired_count}개")

        if pending_count > 0:
            lines.append(f"\n💡 결제 후 아무 메시지나 입력하면 알림이 중단됩니다.")
            lines.append(f"🔗 결제: {settings.KORAIL_PAYMENT_URL}")

        return "\n".join(lines)

    def mark_seat_paid(self, chat_id: int, seat_number: int) -> bool:
        """
        Mark a specific seat as paid.

        Args:
            chat_id: User's chat ID
            seat_number: Seat number to mark as paid

        Returns:
            True if successful, False if seat not found
        """
        status = self.storage.get_multi_reservation_status(chat_id)
        if not status:
            return False

        if status.mark_reservation_paid(seat_number):
            self.storage.save_multi_reservation_status(status)
            logger.info(f"Marked seat {seat_number} as paid for chat_id={chat_id}")
            return True

        return False

    def mark_all_paid(self, chat_id: int) -> bool:
        """
        Mark all reservations as paid (used when user confirms payment completion).

        Args:
            chat_id: User's chat ID

        Returns:
            True if successful
        """
        status = self.storage.get_multi_reservation_status(chat_id)
        if not status:
            return False

        for reservation in status.reservations:
            if reservation.status == ReservationPaymentStatus.PENDING:
                reservation.status = ReservationPaymentStatus.PAID

        status.manually_stopped = True
        self.storage.save_multi_reservation_status(status)
        logger.info(f"Marked all reservations as paid for chat_id={chat_id}")
        return True
