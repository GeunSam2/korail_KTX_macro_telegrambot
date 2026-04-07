"""
Background process for train reservation.

This module is executed as a subprocess to continuously search for
and attempt to reserve trains. It has been refactored to use the new
service architecture while maintaining backward compatibility.
"""
import sys
import requests
from korail2 import TrainType, ReserveOption

# Add src to path
sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from config.settings import settings
from storage import InMemoryStorage
from services import KorailService, TelegramService, PaymentReminderService
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

        # Parse train type
        self.train_type = self._parse_train_type(self.train_type_str)
        self.reserve_option = self._parse_reserve_option(self.special_info_str)

        # Initialize services
        self.storage = InMemoryStorage()
        self.telegram = TelegramService(settings.TELEGRAM_BOT_TOKEN)
        self.payment_reminder = PaymentReminderService(self.storage, self.telegram)
        self.korail = KorailService()

        logger.info(
            f"Initialized background process: {self.src_locate} -> {self.dst_locate} "
            f"on {self.dep_date} for chat_id={self.chat_id}"
        )

    def _parse_train_type(self, train_type_str: str) -> TrainType:
        """Parse train type from string."""
        if "KTX" in train_type_str.upper() and "ALL" not in train_type_str.upper():
            return TrainType.KTX
        else:
            return TrainType.ALL

    def _parse_reserve_option(self, option_str: str) -> ReserveOption:
        """Parse reserve option from string."""
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
                reserve_option=self.reserve_option
            )

            if reservation:
                logger.info(f"Reservation successful: {reservation}")

                # Send success message
                message = f"""
🎉 열차 예약에 성공했습니다!!

예약에 성공한 열차 정보는 다음과 같습니다.
===================
{reservation}
===================

⚠️ 중요: {settings.PAYMENT_TIMEOUT_MINUTES}분내에 사이트에서 결제를 완료하지 않으면 예약이 취소됩니다!

💡 결제 완료 후 아무 메시지나 입력하시면 리마인더 알림이 중단됩니다.
🔗 결제 링크: {settings.KORAIL_PAYMENT_URL}
"""
                self._send_callback(message, status=0)

                # Start payment reminders
                logger.info(f"Starting payment reminders for chat_id={self.chat_id}")
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
