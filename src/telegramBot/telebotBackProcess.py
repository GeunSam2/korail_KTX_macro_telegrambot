"""
Background process for train reservation.

This module is executed as a subprocess to continuously search for
and attempt to reserve trains. It has been refactored to use the new
service architecture while maintaining backward compatibility.
"""
import sys
import requests
from datetime import datetime, timedelta
from korail2 import TrainType, ReserveOption

# Add src to path
sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from config.settings import settings
from storage import InMemoryStorage
from services import KorailService, TelegramService, PaymentReminderService, MultiReservationReminderService
from models import MultiReservationStatus, SingleReservationInfo, ReservationPaymentStatus
from utils.logger import get_logger

logger = get_logger(__name__)

# Set recursion limit
sys.setrecursionlimit(settings.RECURSION_LIMIT)


class BackgroundReservationProcess:
    """Background process for train reservation."""

    def __init__(self):
        """Initialize from command line arguments."""
        if len(sys.argv) < 11:
            logger.error("Insufficient arguments")
            sys.exit(1)

        self.username = sys.argv[1]
        self.password = sys.argv[2]
        self.dep_date = sys.argv[3]
        self.src_locate = sys.argv[4]
        self.dst_locate = sys.argv[5]
        self.dep_time = sys.argv[6]
        self.train_type_str = sys.argv[7]
        self.special_info_str = sys.argv[8]
        self.chat_id = sys.argv[9]
        self.max_dep_time = sys.argv[10]

        # New parameters with defaults for backward compatibility
        self.passenger_count = int(sys.argv[11]) if len(sys.argv) > 11 else 1
        self.seat_strategy = sys.argv[12] if len(sys.argv) > 12 else "consecutive"

        # Parse train type
        self.train_type = self._parse_train_type(self.train_type_str)
        self.reserve_option = self._parse_reserve_option(self.special_info_str)

        # Initialize services
        self.storage = InMemoryStorage()
        self.telegram = TelegramService(settings.TELEGRAM_BOT_TOKEN)
        self.payment_reminder = PaymentReminderService(self.storage, self.telegram)
        self.multi_reminder = MultiReservationReminderService(self.storage, self.telegram)
        self.korail = KorailService()

        logger.info(
            f"Initialized background process: {self.src_locate} -> {self.dst_locate} "
            f"on {self.dep_date} for chat_id={self.chat_id}, "
            f"passengers={self.passenger_count}, strategy={self.seat_strategy}"
        )

    def _parse_train_type(self, train_type_str: str) -> TrainType:
        """Parse train type from string."""
        # Check for exact string representation of enum
        if "TrainType.KTX" in train_type_str:
            return TrainType.KTX
        elif "TrainType.ALL" in train_type_str:
            return TrainType.ALL
        # Check for numeric values (backward compatibility)
        elif train_type_str == "100":  # KTX value
            return TrainType.KTX
        elif train_type_str == "0":  # ALL value
            return TrainType.ALL
        # Fallback to checking for keywords
        elif "KTX" in train_type_str.upper() and "ALL" not in train_type_str.upper():
            return TrainType.KTX
        else:
            return TrainType.ALL

    def _parse_reserve_option(self, option_str: str) -> ReserveOption:
        """Parse reserve option from string."""
        # Check for exact string representation of enum
        if "ReserveOption.GENERAL_FIRST" in option_str:
            return ReserveOption.GENERAL_FIRST
        elif "ReserveOption.GENERAL_ONLY" in option_str:
            return ReserveOption.GENERAL_ONLY
        elif "ReserveOption.SPECIAL_FIRST" in option_str:
            return ReserveOption.SPECIAL_FIRST
        elif "ReserveOption.SPECIAL_ONLY" in option_str:
            return ReserveOption.SPECIAL_ONLY

        # Fallback to checking for keywords
        option_str_upper = option_str.upper()
        if "GENERAL_FIRST" in option_str_upper:
            return ReserveOption.GENERAL_FIRST
        elif "GENERAL_ONLY" in option_str_upper:
            return ReserveOption.GENERAL_ONLY
        elif "SPECIAL_FIRST" in option_str_upper:
            return ReserveOption.SPECIAL_FIRST
        elif "SPECIAL_ONLY" in option_str_upper:
            return ReserveOption.SPECIAL_ONLY
        else:
            return ReserveOption.GENERAL_FIRST

    def run(self):
        """Run the reservation process."""
        try:
            logger.info(f"Logging in as {self.username}...")

            # Login
            if not self.korail.login(self.username, self.password):
                logger.error("Login failed")
                self._send_callback("로그인에 실패했습니다.", status=1)
                return

            logger.info("Login successful, starting reservation loop...")

            # Search and reserve
            reservation = self.korail.search_and_reserve_loop(
                dep_date=self.dep_date,
                src_locate=self.src_locate,
                dst_locate=self.dst_locate,
                dep_time=self.dep_time,
                max_dep_time=self.max_dep_time,
                train_type=self.train_type,
                reserve_option=self.reserve_option,
                passenger_count=self.passenger_count,
                seat_strategy=self.seat_strategy
            )

            if reservation:
                logger.info(f"Reservation successful: {reservation}")

                # Check if this is a random allocation with multiple reservations
                is_random = hasattr(reservation, '_is_random_allocation') and reservation._is_random_allocation
                total_seats = getattr(reservation, '_total_seats', self.passenger_count)

                # Build success message
                if is_random and total_seats > 1:
                    all_reservations = getattr(reservation, '_all_reservations', [reservation])
                    reservation_details = "\n".join([f"좌석 {i+1}: {res}" for i, res in enumerate(all_reservations)])
                    message = f"""
🎉 열차 예약에 성공했습니다!!

총 {total_seats}명의 좌석이 개별적으로 예약되었습니다.
(랜덤 배치 옵션: 좌석이 떨어져 있을 수 있습니다)

예약에 성공한 열차 정보는 다음과 같습니다.
===================
{reservation_details}
===================

⚠️ 중요: {settings.PAYMENT_TIMEOUT_MINUTES}분내에 사이트에서 결제를 완료하지 않으면 예약이 취소됩니다!

💡 결제 완료 후 아무 메시지나 입력하시면 리마인더 알림이 중단됩니다.
🔗 결제 링크: {settings.KORAIL_PAYMENT_URL}
"""

                    # Create MultiReservationStatus for smart reminders
                    self._create_multi_reservation_status(all_reservations, total_seats)

                else:
                    seats_text = f"{self.passenger_count}명" if self.passenger_count > 1 else ""
                    consecutive_text = " (연속된 좌석)" if self.passenger_count > 1 else ""
                    message = f"""
🎉 열차 예약에 성공했습니다!!

{seats_text}{consecutive_text}

예약에 성공한 열차 정보는 다음과 같습니다.
===================
{reservation}
===================

⚠️ 중요: {settings.PAYMENT_TIMEOUT_MINUTES}분내에 사이트에서 결제를 완료하지 않으면 예약이 취소됩니다!

💡 결제 완료 후 아무 메시지나 입력하시면 리마인더 알림이 중단됩니다.
🔗 결제 링크: {settings.KORAIL_PAYMENT_URL}
"""

                self._send_callback(message, status=0)

                # Start appropriate payment reminders
                if is_random and total_seats > 1:
                    logger.info(f"Starting multi-reservation reminders for chat_id={self.chat_id}")
                    self.multi_reminder.start_reminders(int(self.chat_id))
                else:
                    logger.info(f"Starting single payment reminders for chat_id={self.chat_id}")
                    self.payment_reminder.start_reminders(int(self.chat_id))

            else:
                logger.warning("Reservation failed - no result")
                message = """
알수 없는 오류로 예매에 실패했습니다. 처음부터 다시 시도해주세요.

[문제가 없는데 계속 반복되는 경우, 이미 해당 열차가 예매가 되었을 수 있습니다. 사이트를 확인해주세요.]
"""
                self._send_callback(message, status=0)

        except Exception as e:
            logger.error(f"Error in reservation process: {e}", exc_info=True)
            self._send_callback(f"에러발생 : {e}", status=1)

        logger.info(f"Reservation process ended for {self.username}")

    def _create_multi_reservation_status(self, all_reservations: list, total_seats: int) -> None:
        """
        Create MultiReservationStatus for tracking individual seat payment.

        Args:
            all_reservations: List of reservation objects from korail2
            total_seats: Total number of seats reserved
        """
        try:
            now = datetime.now()
            expires_at = now + timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES)

            # Create SingleReservationInfo for each reservation
            reservation_infos = []
            for i, res in enumerate(all_reservations):
                # Extract reservation ID (try to get from korail2 object)
                rsv_id = getattr(res, 'rsv_id', f"unknown_{i+1}")

                info = SingleReservationInfo(
                    reservation_id=rsv_id,
                    reservation_obj=res,
                    reserved_at=now,
                    expires_at=expires_at,
                    status=ReservationPaymentStatus.PENDING,
                    seat_number=i + 1,
                    train_info=str(res)
                )
                reservation_infos.append(info)

            # Create MultiReservationStatus
            multi_status = MultiReservationStatus(
                chat_id=int(self.chat_id),
                reservations=reservation_infos,
                total_seats=total_seats,
                seat_strategy=self.seat_strategy,
                created_at=now,
                manually_stopped=False
            )

            # Save to storage
            self.storage.save_multi_reservation_status(multi_status)
            logger.info(
                f"Created MultiReservationStatus for chat_id={self.chat_id} "
                f"with {len(reservation_infos)} reservations"
            )

        except Exception as e:
            logger.error(f"Failed to create MultiReservationStatus: {e}", exc_info=True)

    def _send_callback(self, message: str, status: int = 0):
        """
        Send callback to main app.

        Args:
            message: Message to send to user
            status: 0 for success/completion, 1 for error
        """
        try:
            callback_url = f"{settings.CALLBACK_BASE_URL}/telebot"
            params = {
                "chatId": self.chat_id,
                "msg": message,
                "status": status
            }

            session = requests.session()
            response = session.get(callback_url, params=params, verify=False, timeout=10)
            logger.debug(f"Callback sent: status={status}, response={response.status_code}")

        except Exception as e:
            logger.error(f"Failed to send callback: {e}")


if __name__ == "__main__":
    process = BackgroundReservationProcess()
    process.run()
