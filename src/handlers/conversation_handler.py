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
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.CANCEL_START_CONFIRMATION)
        else:
            self.telegram.send_message(chat_id, error)

    def _handle_admin_login(self, chat_id: int, session: UserSession) -> None:
        """Handle magic admin login."""
        username = settings.KORAIL_ADMIN_USER_ID
        password = settings.KORAIL_ADMIN_PASSWORD

        if not username or not password:
            session.reset()
            self.storage.save_user_session(session)
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.ERROR_ADMIN_ENV)
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
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.ERROR_ADMIN_LOGIN)

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
        self.telegram.send_message(chat_id, MessageTemplates.request_departure_station())

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

        from telegramBot.messages import Messages
        self.telegram.send_message(chat_id, Messages.REQUEST_DST_STATION)

    def _handle_dep_time_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle departure time input."""
        is_valid, error = InputValidator.validate_time(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        session.train_info['depTime'] = text + "00"  # Add seconds
        session.last_action = UserProgress.DEP_TIME_INPUT_SUCCESS
        self.storage.save_user_session(session)

        from telegramBot.messages import Messages
        self.telegram.send_message(chat_id, Messages.REQUEST_DEP_TIME)

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

        from telegramBot.messages import Messages
        self.telegram.send_message(chat_id, Messages.REQUEST_TRAIN_TYPE)

    def _handle_train_type_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle train type selection."""
        is_valid, error = InputValidator.validate_train_type_choice(text)

        if not is_valid:
            self.telegram.send_message(chat_id, error)
            return

        if text == "1":
            session.train_info['trainType'] = "TrainType.KTX"
            session.train_info['trainTypeShow'] = "KTX"
        else:
            session.train_info['trainType'] = "TrainType.ALL"
            session.train_info['trainTypeShow'] = "ALL"

        session.last_action = UserProgress.TRAIN_TYPE_INPUT_SUCCESS
        self.storage.save_user_session(session)

        from telegramBot.messages import Messages
        self.telegram.send_message(chat_id, Messages.REQUEST_SEAT_TYPE)

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
        from telegramBot.messages import Messages
        self.telegram.send_message(chat_id, Messages.REQUEST_PASSENGER_COUNT)

    def _handle_passenger_count_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle passenger count input."""
        # Validate input
        from telegramBot.messages import Messages
        if not text.isdigit():
            self.telegram.send_message(chat_id, Messages.ERROR_PASSENGER_COUNT_NOT_DIGIT)
            return

        count = int(text)
        if count < 1 or count > 9:
            self.telegram.send_message(chat_id, Messages.ERROR_PASSENGER_COUNT_RANGE)
            return

        # Save passenger count
        session.train_info['passengerCount'] = count
        session.last_action = UserProgress.PASSENGER_COUNT_INPUT_SUCCESS
        self.storage.save_user_session(session)

        # Ask for seat strategy if more than 1 passenger
        if count > 1:
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.REQUEST_SEAT_STRATEGY.format(count=count))
        else:
            # Single passenger, skip seat strategy
            session.train_info['seatStrategy'] = 'consecutive'
            session.last_action = UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
            self.storage.save_user_session(session)
            self._show_final_confirmation(chat_id, session)

    def _handle_seat_strategy_input(self, chat_id: int, text: str, session: UserSession) -> None:
        """Handle seat strategy selection."""
        if text not in ["1", "2"]:
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.ERROR_SEAT_STRATEGY_INVALID)
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

        from telegramBot.messages import Messages
        summary = Messages.CONFIRM_RESERVATION.format(
            depDate=session.train_info['depDate'],
            srcLocate=session.train_info['srcLocate'],
            dstLocate=session.train_info['dstLocate'],
            depTime=session.train_info['depTime'][:4],
            maxDepTime=session.train_info['maxDepTime'],
            trainTypeShow=session.train_info['trainTypeShow'],
            specialInfoShow=session.train_info['specialInfoShow'],
            passengerCount=passenger_count,
            seatStrategy=seat_strategy_display
        )
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
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.CANCELLED_BY_USER)
        else:
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.ERROR_CONFIRM_INVALID)

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
            from telegramBot.messages import Messages
            self.telegram.send_message(chat_id, Messages.ERROR_RESERVATION_START_FAILED)

    def _handle_already_processing(self, chat_id: int, session: UserSession) -> None:
        """Handle message when reservation is already in progress."""
        info = session.train_info
        from telegramBot.messages import Messages
        message = Messages.ALREADY_RUNNING.format(
            depDate=info.get('depDate', 'N/A'),
            srcLocate=info.get('srcLocate', 'N/A'),
            dstLocate=info.get('dstLocate', 'N/A'),
            depTime=info.get('depTime', 'N/A')[:4] if info.get('depTime') else 'N/A',
            trainTypeShow=info.get('trainTypeShow', 'N/A'),
            specialInfoShow=info.get('specialInfoShow', 'N/A')
        )
        self.telegram.send_message(chat_id, message)
