"""In-memory storage implementation (current behavior)."""
from typing import Optional, List, Dict

from models import UserSession, RunningReservation, PaymentStatus
from storage.base import StorageInterface


class InMemoryStorage(StorageInterface):
    """
    In-memory storage implementation.

    This maintains application state in memory (lost on restart).
    Matches the current behavior of the application.
    """

    def __init__(self):
        self._user_sessions: Dict[int, UserSession] = {}
        self._running_reservations: Dict[int, RunningReservation] = {}
        self._payment_statuses: Dict[int, PaymentStatus] = {}
        self._subscribers: set[int] = set()
        self._admin_sessions: set[int] = set()  # Track authenticated admin sessions
        self._admin_password_pending: set[int] = set()  # Track users waiting to enter admin password

    # User Session Management
    def get_user_session(self, chat_id: int) -> Optional[UserSession]:
        """Get user session by chat ID."""
        return self._user_sessions.get(chat_id)

    def save_user_session(self, session: UserSession) -> None:
        """Save or update user session."""
        self._user_sessions[session.chat_id] = session

    def delete_user_session(self, chat_id: int) -> None:
        """Delete user session."""
        if chat_id in self._user_sessions:
            del self._user_sessions[chat_id]

    def get_all_user_sessions(self) -> List[UserSession]:
        """Get all user sessions."""
        return list(self._user_sessions.values())

    # Running Reservation Management
    def get_running_reservation(self, chat_id: int) -> Optional[RunningReservation]:
        """Get running reservation by chat ID."""
        return self._running_reservations.get(chat_id)

    def save_running_reservation(self, reservation: RunningReservation) -> None:
        """Save running reservation."""
        self._running_reservations[reservation.chat_id] = reservation

    def delete_running_reservation(self, chat_id: int) -> None:
        """Delete running reservation."""
        if chat_id in self._running_reservations:
            del self._running_reservations[chat_id]

    def get_all_running_reservations(self) -> List[RunningReservation]:
        """Get all running reservations."""
        return list(self._running_reservations.values())

    # Payment Status Management
    def get_payment_status(self, chat_id: int) -> Optional[PaymentStatus]:
        """Get payment status by chat ID."""
        return self._payment_statuses.get(chat_id)

    def save_payment_status(self, status: PaymentStatus) -> None:
        """Save payment status."""
        self._payment_statuses[status.chat_id] = status

    def delete_payment_status(self, chat_id: int) -> None:
        """Delete payment status."""
        if chat_id in self._payment_statuses:
            del self._payment_statuses[chat_id]

    # Subscriber Management
    def add_subscriber(self, chat_id: int) -> None:
        """Add a subscriber for notifications."""
        self._subscribers.add(chat_id)

    def remove_subscriber(self, chat_id: int) -> None:
        """Remove a subscriber."""
        self._subscribers.discard(chat_id)

    def get_all_subscribers(self) -> List[int]:
        """Get all subscriber chat IDs."""
        return list(self._subscribers)

    def is_subscriber(self, chat_id: int) -> bool:
        """Check if chat ID is a subscriber."""
        return chat_id in self._subscribers

    # Admin Session Management
    def is_admin_authenticated(self, chat_id: int) -> bool:
        """Check if chat ID is authenticated as admin."""
        return chat_id in self._admin_sessions

    def set_admin_authenticated(self, chat_id: int, authenticated: bool = True) -> None:
        """Set admin authentication status for chat ID."""
        if authenticated:
            self._admin_sessions.add(chat_id)
        else:
            self._admin_sessions.discard(chat_id)

    def is_waiting_for_admin_password(self, chat_id: int) -> bool:
        """Check if user is waiting to enter admin password."""
        return chat_id in self._admin_password_pending

    def set_waiting_for_admin_password(self, chat_id: int, waiting: bool = True) -> None:
        """Set whether user is waiting to enter admin password."""
        if waiting:
            self._admin_password_pending.add(chat_id)
        else:
            self._admin_password_pending.discard(chat_id)
