"""
Integration tests for conversation handler.

Tests the multi-step conversation flow for train reservation.
"""
import pytest
from unittest.mock import Mock, patch

from storage import RedisStorage
from services import TelegramService, ReservationService
from handlers import ConversationHandler
from models import UserSession, UserProgress, UserCredentials


class TestConversationHandler:
    """Test conversation handler flows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = RedisStorage()
        self.telegram = Mock(spec=TelegramService)
        self.reservation = Mock(spec=ReservationService)
        self.handler = ConversationHandler(
            self.storage,
            self.telegram,
            self.reservation
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.storage.redis.flushdb()

    def test_start_confirmation_yes(self):
        """Test start confirmation with 'Y'."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.STARTED
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "Y")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.START_ACCEPTED
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "전화번호" in call_args[0][1] or "휴대폰" in call_args[0][1]

    def test_start_confirmation_no(self):
        """Test start confirmation with 'N'."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.STARTED
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "N")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.in_progress is False
        assert updated_session.last_action == 0
        self.telegram.send_message.assert_called_once()

    def test_phone_input_valid(self):
        """Test valid phone number input."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.START_ACCEPTED
        )
        self.storage.save_user_session(session)

        # Add to allow list
        with patch('config.settings.settings.is_user_allowed', return_value=True):
            self.handler.handle_message(chat_id, "010-1234-5678")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.ID_INPUT_SUCCESS
        assert updated_session.credentials.korail_id == "010-1234-5678"
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "비밀번호" in call_args[0][1] or "password" in call_args[0][1].lower()

    def test_phone_input_invalid_format(self):
        """Test invalid phone number format."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.START_ACCEPTED
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "01012345678")

        updated_session = self.storage.get_user_session(chat_id)
        # Should stay in same state
        assert updated_session.last_action == UserProgress.START_ACCEPTED
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "다시" in call_args[0][1] or "하이픈" in call_args[0][1]

    def test_phone_input_not_in_allow_list(self):
        """Test phone number not in allow list."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.START_ACCEPTED
        )
        self.storage.save_user_session(session)

        with patch('config.settings.settings.is_user_allowed', return_value=False):
            self.handler.handle_message(chat_id, "010-9999-9999")

        updated_session = self.storage.get_user_session(chat_id)
        # Should be reset
        assert updated_session.in_progress is False
        self.telegram.send_message.assert_called()

    @patch('services.korail_service.KorailService.login')
    def test_password_input_success(self, mock_login):
        """Test successful password input and login."""
        mock_login.return_value = True
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.ID_INPUT_SUCCESS
        )
        session.credentials = UserCredentials(korail_id="010-1234-5678", korail_pw="")
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "password123")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.PW_INPUT_SUCCESS
        assert updated_session.credentials.korail_pw == "password123"
        mock_login.assert_called_once_with("010-1234-5678", "password123")
        self.telegram.send_message.assert_called_once()

    @patch('services.korail_service.KorailService.login')
    def test_password_input_failure(self, mock_login):
        """Test failed password input."""
        mock_login.return_value = False
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.ID_INPUT_SUCCESS
        )
        session.credentials = UserCredentials(korail_id="010-1234-5678", korail_pw="")
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "wrong_password")

        updated_session = self.storage.get_user_session(chat_id)
        # Should stay in same state for retry
        assert updated_session.last_action == UserProgress.ID_INPUT_SUCCESS
        self.telegram.send_message.assert_called_once()

    def test_date_input_valid(self):
        """Test valid date input."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.PW_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        from datetime import datetime, timedelta
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")

        self.handler.handle_message(chat_id, future_date)

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.DATE_INPUT_SUCCESS
        assert updated_session.train_info['depDate'] == future_date
        self.telegram.send_message.assert_called_once()

    def test_date_input_invalid_past(self):
        """Test invalid past date input."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.PW_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "20200101")

        updated_session = self.storage.get_user_session(chat_id)
        # Should stay in same state
        assert updated_session.last_action == UserProgress.PW_INPUT_SUCCESS
        self.telegram.send_message.assert_called_once()

    def test_station_input_valid(self):
        """Test valid station inputs."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.DATE_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        # Source station
        self.handler.handle_message(chat_id, "서울")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.SRC_LOCATE_INPUT_SUCCESS
        assert updated_session.train_info['srcLocate'] == "서울"

        # Destination station
        self.handler.handle_message(chat_id, "부산")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.DST_LOCATE_INPUT_SUCCESS
        assert updated_session.train_info['dstLocate'] == "부산"

    def test_time_input_valid(self):
        """Test valid time inputs."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.DST_LOCATE_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        # Departure time
        self.handler.handle_message(chat_id, "0900")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.DEP_TIME_INPUT_SUCCESS
        assert updated_session.train_info['depTime'] == "090000"

        # Max departure time
        self.handler.handle_message(chat_id, "1800")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.MAX_DEP_TIME_INPUT_SUCCESS
        assert updated_session.train_info['maxDepTime'] == "1800"

    def test_train_type_selection(self):
        """Test train type selection."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.MAX_DEP_TIME_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        # Select KTX
        self.handler.handle_message(chat_id, "1")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.TRAIN_TYPE_INPUT_SUCCESS
        assert updated_session.train_info['trainType'] == "TrainType.KTX"

    def test_seat_option_selection(self):
        """Test seat option selection."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.TRAIN_TYPE_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        # Select GENERAL_FIRST
        self.handler.handle_message(chat_id, "1")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.SPECIAL_INPUT_SUCCESS

    def test_passenger_count_single(self):
        """Test single passenger count."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.SPECIAL_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "1")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.train_info['passengerCount'] == 1
        assert updated_session.last_action == UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
        assert updated_session.train_info['seatStrategy'] == 'consecutive'

    def test_passenger_count_multiple(self):
        """Test multiple passenger count."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.SPECIAL_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "3")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.train_info['passengerCount'] == 3
        assert updated_session.last_action == UserProgress.PASSENGER_COUNT_INPUT_SUCCESS
        # Should ask for seat strategy
        self.telegram.send_message.assert_called()

    def test_seat_strategy_selection(self):
        """Test seat strategy selection."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.PASSENGER_COUNT_INPUT_SUCCESS
        )
        session.train_info = {'passengerCount': 3}
        self.storage.save_user_session(session)

        # Select consecutive
        self.handler.handle_message(chat_id, "1")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
        assert updated_session.train_info['seatStrategy'] == 'consecutive'

        # Reset and test random
        session.last_action = UserProgress.PASSENGER_COUNT_INPUT_SUCCESS
        self.storage.save_user_session(session)
        self.handler.handle_message(chat_id, "2")
        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.train_info['seatStrategy'] == 'random'

    def test_final_confirmation_yes(self):
        """Test final confirmation with yes."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
        )
        session.credentials = UserCredentials(
            korail_id="010-1234-5678",
            korail_pw="password123"
        )
        session.train_info = {
            'depDate': '20991231',
            'srcLocate': '서울',
            'dstLocate': '부산',
            'depTime': '090000',
            'maxDepTime': '1800',
            'trainType': 'TrainType.KTX',
            'trainTypeShow': 'KTX',
            'specialInfo': 'ReserveOption.GENERAL_FIRST',
            'specialInfoShow': 'GENERAL_FIRST',
            'passengerCount': 1,
            'seatStrategy': 'consecutive'
        }
        self.storage.save_user_session(session)

        self.reservation.start_reservation_process.return_value = True

        self.handler.handle_message(chat_id, "Y")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.last_action == UserProgress.FINDING_TICKET
        self.reservation.start_reservation_process.assert_called_once()

    def test_final_confirmation_no(self):
        """Test final confirmation with no."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.SEAT_STRATEGY_INPUT_SUCCESS
        )
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "N")

        updated_session = self.storage.get_user_session(chat_id)
        assert updated_session.in_progress is False
        assert updated_session.last_action == 0

    def test_already_processing_message(self):
        """Test message when already processing."""
        chat_id = 12345
        session = UserSession(
            chat_id=chat_id,
            in_progress=True,
            last_action=UserProgress.FINDING_TICKET
        )
        session.train_info = {
            'depDate': '20991231',
            'srcLocate': '서울',
            'dstLocate': '부산',
            'depTime': '090000',
            'trainTypeShow': 'KTX',
            'specialInfoShow': 'GENERAL_FIRST'
        }
        self.storage.save_user_session(session)

        self.handler.handle_message(chat_id, "anything")

        # Should send "already running" message
        self.telegram.send_message.assert_called_once()
        call_args = self.telegram.send_message.call_args
        assert "진행" in call_args[0][1] or "running" in call_args[0][1].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
