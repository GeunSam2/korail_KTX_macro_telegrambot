"""Telegram webhook API endpoint."""
from flask import request, make_response
from flask_restful import Resource

from storage.base import StorageInterface
from services import TelegramService, ReservationService, PaymentReminderService, MultiReservationReminderService
from handlers import CommandHandler, ConversationHandler
from models import PaymentStatus
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramWebhook(Resource):
    """
    Flask-RESTful resource for handling Telegram webhook callbacks.

    This replaces the old Index class from telebotApiHandler.py
    """

    def __init__(
        self,
        storage: StorageInterface,
        telegram_service: TelegramService,
        reservation_service: ReservationService,
        payment_reminder_service: PaymentReminderService,
        **kwargs
    ):
        """
        Initialize webhook handler.

        Args:
            storage: Storage interface
            telegram_service: Telegram messaging service
            reservation_service: Reservation service
            payment_reminder_service: Payment reminder service
        """
        super().__init__(**kwargs)
        self.storage = storage
        self.telegram = telegram_service
        self.reservation = reservation_service
        self.payment_reminder = payment_reminder_service

        # Initialize multi-reservation reminder service (singleton for thread tracking)
        self.multi_reminder = MultiReservationReminderService(storage, telegram_service)

        # Initialize handlers
        self.command_handler = CommandHandler(
            storage, telegram_service, reservation_service, payment_reminder_service
        )
        self.conversation_handler = ConversationHandler(
            storage, telegram_service, reservation_service
        )

    def post(self):
        """
        Handle POST request from Telegram webhook.

        This is called when users send messages to the bot.
        """
        try:
            data = request.json

            # Ignore edited messages and chat member updates
            if "edited_message" in data or "my_chat_member" in data:
                return make_response("OK")

            # Extract message
            try:
                message = data['message']
                text = message['text'].strip()
                chat_id = int(message['chat']['id'])
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid message format: {e}")
                return make_response("OK")

            logger.info(f"Received message from chat_id={chat_id}: {text}")

            # Get user session to check progress
            session = self.storage.get_user_session(chat_id)
            in_progress = session.in_progress if session else False
            progress_num = session.last_action if session else 0

            logger.debug(
                f"chat_id={chat_id}, in_progress={in_progress}, "
                f"progress={progress_num}"
            )

            # Check for payment reminder active state (single reservation)
            payment_status = self.storage.get_payment_status(chat_id)
            if payment_status and payment_status.reminder_active and not payment_status.completed:
                # User sent any non-command message during payment reminder
                if text and not text.startswith('/'):
                    self.payment_reminder.confirm_payment(chat_id)
                    return make_response("OK")

            # Check for multi-reservation reminder active state (no current_seat_index set)
            # This handles the case when ALL seats are reserved but waiting for final payment
            multi_status = self.storage.get_multi_reservation_status(chat_id)
            if multi_status and multi_status.should_show_reminder():
                # Check if we're NOT in middle of random seating (no current_seat_index)
                current_seat = self.storage.get_current_seat_index(chat_id)
                if current_seat is None:
                    # All seats reserved, just waiting for payment confirmation
                    if text and not text.startswith('/'):
                        # Mark all as paid and stop reminders
                        self.multi_reminder.mark_all_paid(chat_id)

                        # Send confirmation
                        self.telegram.send_message(
                            chat_id,
                            "✅ 결제 완료 확인!\n\n모든 좌석의 결제 알림이 중단되었습니다."
                        )
                        return make_response("OK")

            # Handle /cancel command first (works in any state)
            if text == "/cancel":
                self.command_handler.handle_cancel(chat_id)
                return make_response("OK")

            # Route commands BEFORE checking random seating state
            # This allows users to use /help, /status even during payment waiting
            if self.command_handler.is_command(text):
                self.command_handler.route_command(chat_id, text)
                return make_response("OK")

            # Check if random seating in progress (waiting for payment confirmation)
            current_seat = self.storage.get_current_seat_index(chat_id)
            if current_seat is not None:  # Random seating in progress
                # ANY message confirms payment and proceeds to next seat
                logger.info(f"Payment confirmed for seat {current_seat} by user message, chat_id={chat_id}")

                # Mark payment ready for background process
                self.storage.mark_payment_ready(chat_id, current_seat)

                # DON'T stop reminders - they should continue running for remaining seats
                # The reminder service will automatically update when new seats are added
                logger.info(f"Payment confirmed, reminders will continue for remaining seats")

                # Send confirmation
                self.telegram.send_message(
                    chat_id,
                    f"✅ {current_seat + 1}번째 좌석 결제 확인!\n\n"
                    f"다음 좌석 예약을 시작합니다..."
                )

                return make_response("OK")

            # Check if waiting for admin password (takes priority over everything)
            if self.storage.is_waiting_for_admin_password(chat_id):
                # User is waiting to enter admin password
                if self.command_handler.handle_admin_password(chat_id, text):
                    # Successfully authenticated
                    return make_response("OK")
                else:
                    # Failed authentication
                    return make_response("OK")

            # Handle conversation flow (non-command messages)
            if in_progress:
                # Handle conversation flow
                self.conversation_handler.handle_message(chat_id, text)
            else:
                # No active session and not a command
                self.telegram.send_message(
                    chat_id,
                    "[진행중인 예약프로세스가 없습니다]\n/start 를 입력하여 작업을 시작하세요."
                )

            return make_response("OK")

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return make_response("OK")  # Still return OK to Telegram

    def get(self):
        """
        Handle GET request for callbacks from background processes.

        This is used by the background reservation process to notify
        the bot about reservation results.
        """
        try:
            # Extract parameters
            chat_id = request.args.get('chatId')
            msg = request.args.get('msg')
            status = request.args.get('status')
            is_multi = request.args.get('isMulti', '0')
            total_seats = request.args.get('totalSeats', '1')
            seat_strategy = request.args.get('seatStrategy', 'consecutive')

            if not all([chat_id, msg, status]):
                logger.warning("Incomplete callback parameters")
                return make_response("OK")

            chat_id = int(chat_id)
            is_multi = (is_multi == '1')
            total_seats = int(total_seats)

            logger.info(
                f"Callback from background process: chat_id={chat_id}, status={status}, "
                f"is_multi={is_multi}, total_seats={total_seats}, seat_strategy={seat_strategy}"
            )

            # Send message to user
            self.telegram.send_message(chat_id, msg)

            # Handle different status codes
            # status=0: Complete success (all reservations done)
            # status=1: Error/failure
            # status=2: Partial success (random seating intermediate notification)

            if str(status) == "2":
                # Partial reservation notification (random seating)
                logger.info(f"Partial reservation notification for chat_id={chat_id}")

                # Check if multi-reservation status exists and start reminders if needed
                multi_status = self.storage.get_multi_reservation_status(chat_id)
                if multi_status:
                    # Start multi-reservation reminders (checks for duplicates internally)
                    self.multi_reminder.start_reminders(chat_id)

                # Message already sent above, no further action needed
                # User will send payment confirmation which will be handled by POST webhook
                return make_response("OK")

            # If reservation successful (status == 0)
            if str(status) == "0":
                logger.info(f"Reservation successful for chat_id={chat_id}")

                # Reset user session
                session = self.storage.get_user_session(chat_id)
                if session:
                    session.reset()
                    self.storage.save_user_session(session)

                # Start appropriate payment reminders
                if is_multi:
                    logger.info(f"Starting multi-reservation reminders for chat_id={chat_id}")
                    # Note: We can't create full MultiReservationStatus here because we don't have
                    # the actual reservation objects. For now, just start single payment reminder.
                    # TODO: Need to pass reservation details through callback or use shared storage (Redis)
                    self.payment_reminder.start_reminders(chat_id)
                else:
                    logger.info(f"Starting single payment reminders for chat_id={chat_id}")
                    self.payment_reminder.start_reminders(chat_id)

                # Clean up running reservation
                self.storage.delete_running_reservation(chat_id)

                # Notify subscribers
                subscribers = self.storage.get_all_subscribers()
                if session and session.credentials:
                    user_id = session.credentials.korail_id
                    self.telegram.send_to_multiple(
                        subscribers,
                        f"{user_id}의 예약이 종료되었습니다."
                    )

            return make_response("OK")

        except Exception as e:
            logger.error(f"Error handling callback: {e}", exc_info=True)
            return make_response("OK")
