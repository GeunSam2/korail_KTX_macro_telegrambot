"""Telegram messaging service."""
import requests
from typing import Optional

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramService:
    """Service for sending messages via Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram service.

        Args:
            bot_token: Telegram bot token (defaults to settings.TELEGRAM_BOT_TOKEN)
        """
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = settings.TELEGRAM_API_BASE_URL.format(token=self.bot_token)
        self.session = requests.session()

    def send_message(self, chat_id: int, text: str) -> bool:
        """
        Send a text message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage"
            params = {
                "chat_id": chat_id,
                "text": text
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()
            logger.info(f"Message sent to chat_id={chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to chat_id={chat_id}: {e}")
            return False

    def send_to_multiple(self, chat_ids: list[int], text: str) -> int:
        """
        Send a message to multiple chats.

        Args:
            chat_ids: List of Telegram chat IDs
            text: Message text to send

        Returns:
            Number of successful sends
        """
        success_count = 0
        for chat_id in chat_ids:
            if self.send_message(chat_id, text):
                success_count += 1
        return success_count


class MessageTemplates:
    """Pre-defined message templates for the bot."""

    @staticmethod
    def welcome_message() -> str:
        """Welcome message when user starts the bot."""
        return """
근삼 코레일 봇을 이용해 주셔사 감사합니다.
본 프로그램은 매진 열차 자동 예약을 위해 제작된 프로그램으로, 결제 직전의 단계인 "예약" 까지만 진행해 주며, 이후 결제는 예약이 완료된 이후 10분 내로 사용자가 직접 해주셔야 합니다.

예매 프로그램을 시작하기 위해 정보를 입력받겠습니다.
예매정보 입력은 다음 순서로 진행됩니다.
================
  1. 코레일 로그인 정보 입력
  2. 출발 희망일 입력
  3. 출발 역 입력
  4. 도착 역 입력
  *. 관리자로 바로 로그인 : 근삼이최고
================

예매 프로세스를 계속 진행하시려면 "예" 또는 "Y"를 입력해주세요.
        """

    @staticmethod
    def request_phone_number() -> str:
        """Request phone number for login."""
        return """
예매 진행을 계속합니다.
예매 진행중, 취소를 원하시면 /cancel 을 입력해주세요.
코레일 로그인의 위해 정보입력을 시작합니다.

(현재는 휴대폰 번호 로그인 기능만을 지원하며, 추가 기능은 이후 추가할 예정입니다.)

코레일 로그인시 사용하는 휴대전화번호를 입력해 주세요.
[ex_ 010-7537-2437] "-" 를 반드시 포함하여 입력바랍니다.
"""

    @staticmethod
    def request_password() -> str:
        """Request password for login."""
        return """
아이디 입력에 성공하였습니다.
비밀번호를 입력해주십시오.
"""

    @staticmethod
    def login_success() -> str:
        """Login success message."""
        return """
로그인에 성공하였습니다.
예매 희망일 8자를 입력해주십시오.
(ex_ 20230101) <- 2030년 1월 1일
"""

    @staticmethod
    def login_failure(username: str) -> str:
        """Login failure message."""
        return f"""
로그인에 실패하였습니다. 로그인에 사용한 정보는 다음과 같습니다.
==============
아이디 : {username}
암호 : 보안상 공개불가
==============
'Y'또는 '예'를 입력하시면 계정정보를 다시 입력합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
아이디를 그대로 다시 로그인 시도를 하시려면 암호를 입력하세요.

5회 이상 로그인 실패할 경우, 홈페이지를 통해 비밀번호를 재설정하셔야합니다.
"""

    @staticmethod
    def request_departure_date() -> str:
        """Request departure date."""
        return """
출발일 입력에 성공하였습니다.
출발역을 입력해주십시오.

역 정보를 참고하시려면 다음 사이트를 이용하세요. http://www.letskorail.com/ebizprd/stationKtxList.do
['역' 을 제외한 이름을 입력해주세요.]
(ex_ 광명)
"""

    @staticmethod
    def request_arrival_station() -> str:
        """Request arrival station."""
        return """
출발역 입력이 완료되었습니다.
도착역을 입력해 주십시오.

역 정보를 참고하시려면 다음 사이트를 이용하세요. http://www.letskorail.com/ebizprd/stationKtxList.do
['역' 을 제외한 이름을 입력해주세요.]
(ex_ 광주송정)
"""

    @staticmethod
    def reservation_success(reservation_info: str) -> str:
        """Reservation success message."""
        return f"""
🎉 열차 예약에 성공했습니다!!

예약에 성공한 열차 정보는 다음과 같습니다.
===================
{reservation_info}
===================

⚠️ 중요: 10분내에 사이트에서 결제를 완료하지 않으면 예약이 취소됩니다!

💡 결제 완료 후 아무 메시지나 입력하시면 리마인더 알림이 중단됩니다.
🔗 결제 링크: {settings.KORAIL_PAYMENT_URL}
"""

    @staticmethod
    def payment_reminder(remaining_minutes: int, remaining_seconds: int) -> str:
        """Payment reminder message."""
        if remaining_seconds == 0:
            time_text = f"{remaining_minutes}분"
        else:
            time_text = f"{remaining_minutes}분 {remaining_seconds}초"

        return f"""
⏰ 결제 리마인더 ⏰
예약 취소까지 남은 시간: {time_text}

서둘러 결제를 완료해주세요!
💡 결제 완료 시 아무 메시지나 입력하면 알림이 중단됩니다.
🔗 {settings.KORAIL_PAYMENT_URL}
"""

    @staticmethod
    def payment_confirmed() -> str:
        """Payment confirmation message."""
        return """
✅ 결제 완료 확인되었습니다!
리마인더 알림이 곧 중단됩니다.
즐거운 여행 되세요! 🚄
"""

    @staticmethod
    def help_message() -> str:
        """Help message with available commands."""
        return """
- 예약 시작 : /start
- 결제 완료 : /결제완료 (리마인더 중단)
- 구독 시작 : /subscribe
- 예약 상태 확인 : /status
- 전체 취소 : /cancelall
- 전체 유저 확인 : /allusers
- 공지 : /broadcast [메시지]
"""

    @staticmethod
    def not_in_allow_list() -> str:
        """Message when user is not in allow list."""
        return """
2024년 부터 본 서비스가 유료화 되었습니다.
구독을 희망하시면 텔레그램 @dubidum 으로 문의주세요.
예매 진행을 취소합니다.
"""

    @staticmethod
    def reservation_cancelled() -> str:
        """Reservation cancelled message."""
        return "예약이 취소되었습니다."

    @staticmethod
    def reservation_started() -> str:
        """Reservation process started message."""
        return """
예약 프로그램 동작이 시작되었습니다.
매진된 자리에 공석이 생길 때 까지 근삼봇이 열심히 찾아볼게요!
예약에 성공하면 여기로 다시 알려줄게요!
[신규기능!] 진행중인 예약을 그만 두시고 싶으시면 /cancel을 입력해주세요!
"""
