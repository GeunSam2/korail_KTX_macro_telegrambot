"""Payment status check API endpoint."""
from flask import request
from flask_restful import Resource

from storage.base import StorageInterface
from utils.logger import get_logger

logger = get_logger(__name__)


class PaymentCheckAPI(Resource):
    """
    API endpoint to check payment completion status.

    Used by payment reminder service to check if user has completed payment.
    """

    def __init__(self, storage: StorageInterface, **kwargs):
        """
        Initialize payment check API.

        Args:
            storage: Storage interface
        """
        super().__init__(**kwargs)
        self.storage = storage

    def get(self):
        """
        Check payment status for a chat ID.

        Query params:
            chatId: Telegram chat ID

        Returns:
            JSON: {"completed": bool}
        """
        try:
            chat_id_str = request.args.get('chatId')

            if not chat_id_str:
                logger.warning("Payment check called without chatId")
                return {'completed': False}

            chat_id = int(chat_id_str)

            # Get payment status from storage
            payment_status = self.storage.get_payment_status(chat_id)

            if payment_status:
                completed = payment_status.completed
                logger.debug(f"Payment status for chat_id={chat_id}: {completed}")
                return {'completed': completed}
            else:
                logger.debug(f"No payment status found for chat_id={chat_id}")
                return {'completed': False}

        except ValueError as e:
            logger.error(f"Invalid chat_id format: {e}")
            return {'completed': False}
        except Exception as e:
            logger.error(f"Error checking payment status: {e}", exc_info=True)
            return {'completed': False}
