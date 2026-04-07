"""Integration tests for refactored application."""
import sys
import pytest

# Add src to path
sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from config.settings import settings
from storage import InMemoryStorage
from services import TelegramService, KorailService, ReservationService, PaymentReminderService
from handlers import CommandHandler, ConversationHandler
from models import UserSession, UserProgress, UserCredentials


class TestRefactoredArchitecture:
    """Test the refactored architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryStorage()
        self.telegram = TelegramService("test_token")
        self.reservation = ReservationService(self.storage, self.telegram)
        self.payment_reminder = PaymentReminderService(self.storage, self.telegram)

    def test_storage_user_session(self):
        """Test storage can save and retrieve user sessions."""
        session = UserSession(
            chat_id=12345,
            in_progress=True,
            last_action=UserProgress.STARTED
        )

        self.storage.save_user_session(session)
        retrieved = self.storage.get_user_session(12345)

        assert retrieved is not None
        assert retrieved.chat_id == 12345
        assert retrieved.in_progress is True
        assert retrieved.last_action == UserProgress.STARTED

    def test_storage_payment_status(self):
        """Test storage can manage payment status."""
        from models import PaymentStatus

        status = PaymentStatus(chat_id=12345, completed=False)
        self.storage.save_payment_status(status)

        retrieved = self.storage.get_payment_status(12345)
        assert retrieved is not None
        assert retrieved.completed is False

        # Update status
        retrieved.completed = True
        self.storage.save_payment_status(retrieved)

        updated = self.storage.get_payment_status(12345)
        assert updated.completed is True

    def test_storage_subscribers(self):
        """Test storage can manage subscribers."""
        assert len(self.storage.get_all_subscribers()) == 0

        self.storage.add_subscriber(111)
        self.storage.add_subscriber(222)

        assert len(self.storage.get_all_subscribers()) == 2
        assert self.storage.is_subscriber(111)
        assert self.storage.is_subscriber(222)
        assert not self.storage.is_subscriber(333)

        self.storage.remove_subscriber(111)
        assert len(self.storage.get_all_subscribers()) == 1
        assert not self.storage.is_subscriber(111)

    def test_command_handler_initialization(self):
        """Test command handler can be initialized."""
        handler = CommandHandler(
            self.storage,
            self.telegram,
            self.reservation,
            self.payment_reminder
        )

        assert handler is not None
        assert handler.storage == self.storage

    def test_conversation_handler_initialization(self):
        """Test conversation handler can be initialized."""
        handler = ConversationHandler(
            self.storage,
            self.telegram,
            self.reservation
        )

        assert handler is not None
        assert handler.storage == self.storage

    def test_user_session_reset(self):
        """Test user session can be reset."""
        session = UserSession(
            chat_id=12345,
            in_progress=True,
            last_action=UserProgress.FINDING_TICKET
        )
        session.credentials = UserCredentials(
            korail_id="010-1234-5678",
            korail_pw="password"
        )
        session.train_info = {"depDate": "20230101"}

        session.reset()

        assert session.in_progress is False
        assert session.last_action == 0
        assert session.train_info == {}
        assert session.process_id == 9999999

    def test_settings_validation(self):
        """Test settings validation."""
        # Settings should have required attributes
        assert hasattr(settings, 'TELEGRAM_BOT_TOKEN')
        assert hasattr(settings, 'PAYMENT_TIMEOUT_MINUTES')
        assert hasattr(settings, 'KORAIL_SEARCH_INTERVAL')

    def test_input_validators(self):
        """Test input validators."""
        from utils.validators import InputValidator

        # Phone number validation
        valid, error = InputValidator.validate_phone_number("010-1234-5678")
        assert valid is True

        valid, error = InputValidator.validate_phone_number("01012345678")
        assert valid is False

        # Date validation
        valid, error = InputValidator.validate_date("20991231")
        assert valid is True

        valid, error = InputValidator.validate_date("20200101")
        assert valid is False  # Past date

        valid, error = InputValidator.validate_date("invalid")
        assert valid is False

        # Time validation
        valid, error = InputValidator.validate_time("1430")
        assert valid is True

        valid, error = InputValidator.validate_time("2560")
        assert valid is False  # Invalid hour

    def test_message_templates(self):
        """Test message templates exist."""
        from services.telegram_service import MessageTemplates

        welcome = MessageTemplates.welcome_message()
        assert isinstance(welcome, str)
        assert len(welcome) > 0

        help_msg = MessageTemplates.help_message()
        assert isinstance(help_msg, str)
        assert "/start" in help_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
