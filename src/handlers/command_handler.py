"""Command handler for Telegram bot commands."""
from typing import Optional

from config.settings import settings
from models import UserSession, UserProgress, UserCredentials
from storage.base import StorageInterface
from services import TelegramService, ReservationService, MessageTemplates, KorailService, PaymentReminderService
from utils.logger import get_logger

logger = get_logger(__name__)


class CommandHandler:
    """Handles Telegram bot commands like /start, /cancel, etc."""

    def __init__(
        self,
        storage: StorageInterface,
        telegram_service: TelegramService,
        reservation_service: ReservationService,
        payment_reminder_service: PaymentReminderService
    ):
        """
        Initialize command handler.

        Args:
            storage: Storage interface
            telegram_service: Telegram messaging service
            reservation_service: Reservation service
            payment_reminder_service: Payment reminder service
        """
        self.storage = storage
        self.telegram = telegram_service
        self.reservation = reservation_service
        self.payment_reminder = payment_reminder_service

    def handle_start(self, chat_id: int) -> None:
        """
        Handle /start command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /start for chat_id={chat_id}")

        # Get or create user session
        session = self.storage.get_user_session(chat_id)
        if not session:
            session = UserSession(
                chat_id=chat_id,
                in_progress=False,
                last_action=UserProgress.INIT
            )
            self.storage.save_user_session(session)

        # Update session state
        session.in_progress = True
        session.last_action = UserProgress.STARTED
        self.storage.save_user_session(session)

        # Send welcome message
        self.telegram.send_message(chat_id, MessageTemplates.welcome_message())

    def handle_cancel(self, chat_id: int) -> None:
        """
        Handle /cancel command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /cancel for chat_id={chat_id}")

        # Cancel any running reservation
        self.reservation.cancel_reservation(chat_id)

        # Reset user session
        session = self.storage.get_user_session(chat_id)
        if session:
            session.reset()
            self.storage.save_user_session(session)

    def handle_payment_done(self, chat_id: int) -> None:
        """
        Handle /결제완료 or /paymentdone command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /paymentdone for chat_id={chat_id}")

        # Confirm payment
        self.payment_reminder.confirm_payment(chat_id)

        # Send confirmation
        self.telegram.send_message(chat_id, MessageTemplates.payment_confirmed())

    def handle_subscribe(self, chat_id: int) -> None:
        """
        Handle /subscribe command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /subscribe for chat_id={chat_id}")

        if self.storage.is_subscriber(chat_id):
            message = "이미 구독했습니다."
        else:
            self.storage.add_subscriber(chat_id)
            message = "열차 이용정보 구독 설정이 완료되었습니다."

        self.telegram.send_message(chat_id, message)

    def handle_status(self, chat_id: int) -> None:
        """
        Handle /status command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /status for chat_id={chat_id}")

        status_message = self.reservation.get_status(chat_id)
        self.telegram.send_message(chat_id, status_message)

    def handle_cancel_all(self, chat_id: int) -> None:
        """
        Handle /cancelall command (admin only).

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /cancelall for chat_id={chat_id}")

        # This is an admin command - in production, you'd want to check permissions
        count = self.reservation.cancel_all_reservations(chat_id)
        logger.info(f"Cancelled {count} reservations by admin chat_id={chat_id}")

    def handle_all_users(self, chat_id: int) -> None:
        """
        Handle /allusers command (admin only).

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /allusers for chat_id={chat_id}")

        sessions = self.storage.get_all_user_sessions()
        user_ids = []

        for session in sessions:
            if session.credentials:
                user_ids.append(session.credentials.korail_id)
            else:
                user_ids.append(f"chat_{session.chat_id}")

        message = f"총 {len(user_ids)}명의 유저가 있습니다 : {user_ids}"
        self.telegram.send_message(chat_id, message)

    def handle_broadcast(self, chat_id: int, message: str) -> None:
        """
        Handle /broadcast command (admin only).

        Args:
            chat_id: Admin chat ID
            message: Message to broadcast
        """
        logger.info(f"Handling /broadcast for chat_id={chat_id}")

        # Get all user chat IDs
        sessions = self.storage.get_all_user_sessions()
        all_chat_ids = [s.chat_id for s in sessions]

        if message:
            sent_count = self.telegram.send_to_multiple(all_chat_ids, message)
            logger.info(f"Broadcast sent to {sent_count}/{len(all_chat_ids)} users")
        else:
            # Default fun message if no message provided
            self.telegram.send_to_multiple(all_chat_ids, "앙 기모띠")

    def handle_help(self, chat_id: int) -> None:
        """
        Handle /help command.

        Args:
            chat_id: Telegram chat ID
        """
        logger.info(f"Handling /help for chat_id={chat_id}")
        self.telegram.send_message(chat_id, MessageTemplates.help_message())

    def handle_unknown_command(self, chat_id: int, command: str) -> None:
        """
        Handle unknown commands.

        Args:
            chat_id: Telegram chat ID
            command: Unknown command text
        """
        logger.warning(f"Unknown command '{command}' from chat_id={chat_id}")
        self.telegram.send_message(chat_id, "잘못된 명령어 입니다.")

    def is_command(self, text: str) -> bool:
        """
        Check if text is a command.

        Args:
            text: Message text

        Returns:
            True if text starts with '/'
        """
        return text and text.startswith('/')

    def route_command(self, chat_id: int, text: str) -> bool:
        """
        Route command to appropriate handler.

        Args:
            chat_id: Telegram chat ID
            text: Command text

        Returns:
            True if command was handled, False otherwise
        """
        if not self.is_command(text):
            return False

        # Parse command and arguments
        parts = text.split(' ', 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Route to handler
        if command == "/start":
            self.handle_start(chat_id)
        elif command == "/cancel":
            self.handle_cancel(chat_id)
        elif command in ["/결제완료", "/paymentdone"]:
            self.handle_payment_done(chat_id)
        elif command == "/subscribe":
            self.handle_subscribe(chat_id)
        elif command == "/status":
            self.handle_status(chat_id)
        elif command == "/cancelall":
            self.handle_cancel_all(chat_id)
        elif command == "/allusers":
            self.handle_all_users(chat_id)
        elif command == "/broadcast":
            self.handle_broadcast(chat_id, args)
        elif command == "/help":
            self.handle_help(chat_id)
        else:
            self.handle_unknown_command(chat_id, command)

        return True
