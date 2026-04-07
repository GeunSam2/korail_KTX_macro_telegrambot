"""Conversation flow handler for reservation process."""
from korail2 import TrainType, ReserveOption

from config.settings import settings
from models import UserSession, UserProgress, UserCredentials, TrainSearchParams
from storage.base import StorageInterface
from services import TelegramService, KorailService, ReservationService, MessageTemplates
from utils.validators import InputValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class ConversationHandler:
    """Handles multi-step conversation flow for train reservation."""

    def __init__(
        self,
        storage: StorageInterface,
        telegram_service: TelegramService,
        reservation_service: ReservationService
    ):
        """
        Initialize conversation handler.

        Args:
            storage: Storage interface
            telegram_service: Telegram messaging service
            reservation_service: Reservation service
        """
        self.storage = storage
        self.telegram = telegram_service
        self.reservation = reservation_service

    def handle_message(self, chat_id: int, text: str) -> None:
        """
        Handle user message based on current conversation state.

        Args:
            chat_id: Telegram chat ID
            text: User's message text
        """
        # Get user session
        session = self.storage.get_user_session(chat_id)
        if not session:
            logger.warning(f"No session found for chat_id={chat_id}")
            self.telegram.send_message(
                chat_id,
                "[진행중인 예약프로세스가 없습니다]\n/start 를 입력하여 작업을 시작하세요."
            )
            return

        # Check if already finding ticket
        if session.last_action == UserProgress.FINDING_TICKET:
            self._handle_already_processing(chat_id, session)
            return

        # Route to appropriate handler based on progress
        progress = session.last_action

        if progress == UserProgress.STARTED:
            self._handle_start_confirmation(chat_id, text, session)
        elif progress == UserProgress.START_ACCEPTED:
            self._handle_phone_input(chat_id, text, session)
        elif progress == UserProgress.ID_INPUT_SUCCESS:
            self._handle_password_input(chat_id, text, session)
        elif progress == UserProgress.PW_INPUT_SUCCESS:
            self._handle_date_input(chat_id, text, session)
        elif progress == UserProgress.DATE_INPUT_SUCCESS:
            self._handle_src_station_input(chat_id, text, session)
        elif progress == UserProgress.SRC_LOCATE_INPUT_SUCCESS:
            self._handle_dst_station_input(chat_id, text, session)
        elif progress == UserProgress.DST_LOCATE_INPUT_SUCCESS:
            self._handle_dep_time_input(chat_id, text, session)
        elif progress == UserProgress.DEP_TIME_INPUT_SUCCESS:
            self._handle_max_dep_time_input(chat_id, text, session)
        elif progress == UserProgress.MAX_DEP_TIME_INPUT_SUCCESS:
            self._handle_train_type_input(chat_id, text, session)
        elif progress == UserProgress.TRAIN_TYPE_INPUT_SUCCESS:
            self._handle_special_option_input(chat_id, text, session)
        elif progress == UserProgress.SPECIAL_INPUT_SUCCESS:
            self._handle_passenger_count_input(chat_id, text, session)
        elif progress == UserProgress.PASSENGER_COUNT_INPUT_SUCCESS:
            self._handle_seat_strategy_input(chat_id, text, session)
        elif progress == UserProgress.SEAT_STRATEGY_INPUT_SUCCESS:
            self._handle_final_confirmation(chat_id, text, session)
        else:
            logger.error(f"Unknown progress state: {progress}")
            self.telegram.send_message(
                chat_id,
                "이상이 발생했습니다. /cancel 이나 /start 를 통해 다시 프로그램을 시작해주세요."
            )

    def _handle_start_confirmation(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle initial start confirmation (Y/N)."""
        # Check for magic admin login
        if text == settings.ADMIN_MAGIC_STRING:
            self._handle_admin_login(chat_id, session)
            return

        is_yes, error = InputValidator.validate_yes_no(text)

        if is_yes is True:
            session.last_action = UserProgress.START_ACCEPTED
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, MessageTemplates.request_phone_number())
        elif is_yes is False:
            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, "예매 진행을 취소합니다.")
        else:
            self.telegram.send_message(chat_id, error)

    def _handle_admin_login(self, chat_id: int, session: UserSession) -> None:
        """Handle magic admin login."""
        username = settings.KORAIL_ADMIN_USER_ID
        password = settings.KORAIL_ADMIN_PASSWORD

        if not username or not password:
            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, "컨테이너에 환경변수가 초기화되지 않았습니다.")
            return

        # Try login
        korail = KorailService()
        if korail.login(username, password):
            session.credentials = UserCredentials(korail_id=username, korail_pw=password)
            session.last_action = UserProgress.PW_INPUT_SUCCESS
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, MessageTemplates.login_success())
        else:
            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, "관리자 계정으로 로그인에 문제가 발생하였습니다.")

    def _handle_phone_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle phone number input."""
        is_valid, error = InputValidator.validate_phone_number(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error + " 다시 입력 바랍니다.")
            return

        # Check allow list
        if not settings.is_user_allowed(text):
            # Notify subscribers
            subscribers = self.storage.get_all_subscribers()
            self.telegram.send_to_multiple(
                subscribers,
                f"{text}가 구독자 목록에 없어서 실행에 실패했음."
            )

            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, MessageTemplates.not_in_allow_list())
            return

        # Save phone number
        if not session.credentials:
            session.credentials = UserCredentials(korail_id=text, korail_pw="")
        else:
            session.credentials.korail_id = text

        session.last_action = UserProgress.ID_INPUT_SUCCESS
        self.storage.save_user_session(session)
        self.telegram.send_message(chat_id, MessageTemplates.request_password())

    def _handle_password_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle password input and login."""
        username = session.credentials.korail_id
        password = text

        # Update credentials
        session.credentials.korail_pw = password
        self.storage.save_user_session(session)

        # Try login
        korail = KorailService()
        if korail.login(username, password):
            session.last_action = UserProgress.PW_INPUT_SUCCESS
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, MessageTemplates.login_success())
        else:
            # Login failed - ask for retry
            self.telegram.send_message(chat_id, MessageTemplates.login_failure(username))
            # Don't change state - wait for retry input

    def _handle_date_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle departure date input."""
        is_valid, error = InputValidator.validate_date(text)

        if not is_valid:
            self.telegram.send_message(
                chat_id,
                f"{error}\n예매 희망일 8자를 입력해주십시오.\n(ex_ 20210124) <- 2021년 1월 24일"
            )
            return

        session.train_info['depDate'] = text
        session.last_action = UserProgress.DATE_INPUT_SUCCESS
        self.storage.save_user_session(session)
        self.telegram.send_message(chat_id, MessageTemplates.request_departure_date())

    def _handle_src_station_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle source station input."""
        is_valid, error = InputValidator.validate_station_name(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        session.train_info['srcLocate'] = text
        session.last_action = UserProgress.SRC_LOCATE_INPUT_SUCCESS
        self.storage.save_user_session(session)
        self.telegram.send_message(chat_id, MessageTemplates.request_arrival_station())

    def _handle_dst_station_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle destination station input."""
        is_valid, error = InputValidator.validate_station_name(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        session.train_info['dstLocate'] = text
        session.last_action = UserProgress.DST_LOCATE_INPUT_SUCCESS
        self.storage.save_user_session(session)

        message = """
도착역 입력이 완료되었습니다.
열차 검색을 시작할 기준 시각정보를 입력해주세요.

형식은 HHMM (HH : 시, MM : 분)이며 0-23시 기준입니다. 반드시 4자리로 입력해 주십시오.
(ex_ 13시 5분 이후 기차만 검색 : 1305)
"""
        self.telegram.send_message(chat_id, message)

    def _handle_dep_time_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle departure time input."""
        is_valid, error = InputValidator.validate_time(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        session.train_info['depTime'] = text + "00"  # Add seconds
        session.last_action = UserProgress.DEP_TIME_INPUT_SUCCESS
        self.storage.save_user_session(session)

        message = """
열차 검색 시작 기준 시각 입력이 완료되었습니다.
열차 검색 최대 임계 시각정보를 입력해주세요.

* 임계시각을 지정하지 않으시려면 2400을 입력하세요.(권장)

형식은 HHMM (HH : 시, MM : 분)이며 0-23시 기준입니다. 반드시 4자리로 입력해 주십시오.
(ex_ 13시 5분 이전 기차만 검색 : 1305)
"""
        self.telegram.send_message(chat_id, message)

    def _handle_max_dep_time_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle max departure time input."""
        # Allow 2400 as special value
        if text == "2400":
            is_valid = True
        else:
            is_valid, error = InputValidator.validate_time(text)
            if not is_valid:
                self.telegram.send_message(chat_id, error)
                return

        session.train_info['maxDepTime'] = text
        session.last_action = UserProgress.MAX_DEP_TIME_INPUT_SUCCESS
        self.storage.save_user_session(session)

        message = """
기준 시각 입력이 완료되었습니다.
이용할 열차의 타입을 선택해 주십시오.

=================
1. KTX 및 KTX-산천 열차만 예약
2. 모든 열차 형식 포함하여 예약
=================

1 또는 2를 입력해 주십시오.
"""
        self.telegram.send_message(chat_id, message)

    def _handle_train_type_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle train type selection."""
        is_valid, error = InputValidator.validate_train_type_choice(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        if text == "1":
            session.train_info['trainType'] = str(TrainType.KTX)
            session.train_info['trainTypeShow'] = "KTX"
        else:
            session.train_info['trainType'] = str(TrainType.ALL)
            session.train_info['trainTypeShow'] = "ALL"

        session.last_action = UserProgress.TRAIN_TYPE_INPUT_SUCCESS
        self.storage.save_user_session(session)

        message = """
이용할 열차의 타입 입력이 완료되었습니다.
특실 예매에 대한 타입을 입력해 주십시오.

=================
1. 일반실 우선 예약
2. 일반실만 예약
3. 특실 우선 예약
4. 특실만 예약
=================

1, 2, 3, 4 중 하나를 선택해 주십시오.
"""
        self.telegram.send_message(chat_id, message)

    def _handle_special_option_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle special seat option selection."""
        is_valid, error = InputValidator.validate_special_option_choice(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        option_map = {
            "1": (ReserveOption.GENERAL_FIRST, "GENERAL_FIRST"),
            "2": (ReserveOption.GENERAL_ONLY, "GENERAL_ONLY"),
            "3": (ReserveOption.SPECIAL_FIRST, "SPECIAL_FIRST"),
            "4": (ReserveOption.SPECIAL_ONLY, "SPECIAL_ONLY"),
        }

        option, option_display = option_map[text]
        session.train_info['specialInfo'] = str(option)
        session.train_info['specialInfoShow'] = option_display

        session.last_action = UserProgress.SPECIAL_INPUT_SUCCESS
        self.storage.save_user_session(session)

        # Ask for passenger count
        message = """
특실 예매 타입 입력이 완료되었습니다.
탑승 인원수를 입력해 주십시오.

💡 1~9명까지 선택 가능합니다.
(현재는 성인 인원수만 지원합니다)

예) 2명이 탑승하는 경우: 2
"""
        self.telegram.send_message(chat_id, message)

    def _handle_passenger_count_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle passenger count input."""
        # Validate input
        if not text.isdigit():
            self.telegram.send_message(chat_id, "숫자를 입력해주세요. (1~9)")
            return

        count = int(text)
        if count < 1 or count > 9:
            self.telegram.send_message(chat_id, "1~9명 사이의 인원수를 입력해주세요.")
            return

        # Save passenger count
        session.train_info['passengerCount'] = count
        session.last_action = UserProgress.PASSENGER_COUNT_INPUT_SUCCESS
        self.storage.save_user_session(session)

        # Ask for seat strategy if more than 1 passenger
        if count > 1:
            message = f"""
인원수 입력이 완료되었습니다. (총 {count}명)

좌석 배치 방식을 선택해 주십시오.

=================
1. 연속 좌석 (권장)
   - 같이 앉을 수 있도록 연속된 좌석 예약
   - 연속된 좌석이 없으면 예약 실패

2. 랜덤 배치
   - 한 자리씩 개별적으로 예약
   - 좌석이 떨어져 있을 수 있음
   - 예약 성공률이 더 높음
=================

1 또는 2를 입력해 주십시오.
"""
            self.telegram.send_message(chat_id, message)
        else:
            # Single passenger, skip seat strategy
            session.train_info['seatStrategy'] = 'consecutive'
            session.last_action = UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
            self.storage.save_user_session(session)
            self._show_final_confirmation(chat_id, session)

    def _handle_seat_strategy_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle seat strategy selection."""
        if text not in ["1", "2"]:
            self.telegram.send_message(chat_id, "1 또는 2를 입력해주세요.")
            return

        strategy = "consecutive" if text == "1" else "random"
        strategy_display = "연속 좌석" if text == "1" else "랜덤 배치"

        session.train_info['seatStrategy'] = strategy
        session.train_info['seatStrategyShow'] = strategy_display
        session.last_action = UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
        self.storage.save_user_session(session)

        self._show_final_confirmation(chat_id, session)

    def _show_final_confirmation(self, chat_id: int, session: UserSession) -> None:
        """Show final confirmation summary."""
        passenger_count = session.train_info.get('passengerCount', 1)
        seat_strategy_display = session.train_info.get('seatStrategyShow', '1명')

        summary = f"""
모든 정보 입력이 완료되었습니다.
정보를 확인하십시오.
===================
출발일 : {session.train_info['depDate']}
출발역 : {session.train_info['srcLocate']}
도착역 : {session.train_info['dstLocate']}
검색기준시각 : {session.train_info['depTime'][:4]}
검색최대시각 : {session.train_info['maxDepTime']}
열차타입 : {session.train_info['trainTypeShow']}
특실여부 : {session.train_info['specialInfoShow']}
탑승인원 : {passenger_count}명
좌석배치 : {seat_strategy_display}
===================

'Y'또는 '예'를 입력하시면 예약을 시작합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
예약 완료에 오랜 시간이 걸릴 수 있습니다.
"""
        self.telegram.send_message(chat_id, summary)

    def _handle_final_confirmation(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle final confirmation before starting reservation."""
        is_yes, error = InputValidator.validate_yes_no(text)

        if is_yes is True:
            # Start reservation process
            self._start_reservation(chat_id, session)
        elif is_yes is False:
            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(chat_id, "예약 작업이 취소되었습니다.")
        else:
            message = """
입력하신 값이 선택지에 없습니다.
'Y'또는 '예'를 입력하시면 예약을 시작합니다.
'N'또는 '아니오'를 입력하시면 작업을 취소합니다.
"""
            self.telegram.send_message(chat_id, message)

    def _start_reservation(self, chat_id: int, session: UserSession) -> None:
        """Start the reservation background process."""
        # Create search params
        search_params = TrainSearchParams(
            dep_date=session.train_info['depDate'],
            src_locate=session.train_info['srcLocate'],
            dst_locate=session.train_info['dstLocate'],
            dep_time=session.train_info['depTime'],
            max_dep_time=session.train_info['maxDepTime'],
            train_type=session.train_info['trainType'],
            train_type_display=session.train_info['trainTypeShow'],
            special_option=session.train_info['specialInfo'],
            special_option_display=session.train_info['specialInfoShow'],
            passenger_count=session.train_info.get('passengerCount', 1),
            seat_strategy=session.train_info.get('seatStrategy', 'consecutive')
        )

        # Update session
        session.last_action = UserProgress.FINDING_TICKET
        self.storage.save_user_session(session)

        # Start reservation
        success = self.reservation.start_reservation_process(
            chat_id=chat_id,
            username=session.credentials.korail_id,
            password=session.credentials.korail_pw,
            search_params=search_params
        )

        if not success:
            logger.error(f"Failed to start reservation for chat_id={chat_id}")
            session.reset()
            self.storage.save_user_session(session)
            self.telegram.send_message(
                chat_id,
                "예약 프로세스 시작에 실패했습니다. 다시 시도해주세요."
            )

    def _handle_already_processing(self, chat_id: int, session: UserSession) -> None:
        """Handle message when reservation is already in progress."""
        info = session.train_info
        message = f"""
현재 예매가 이미 진행중입니다.
===================
출발일 : {info.get('depDate', 'N/A')}
출발역 : {info.get('srcLocate', 'N/A')}
도착역 : {info.get('dstLocate', 'N/A')}
검색기준시각 : {info.get('depTime', 'N/A')[:4]}
열차타입 : {info.get('trainTypeShow', 'N/A')}
특실여부 : {info.get('specialInfoShow', 'N/A')}
===================

진행중인 예매를 취소하고 싶으시면 /cancel 을 입력해주세요.
"""
        self.telegram.send_message(chat_id, message)
