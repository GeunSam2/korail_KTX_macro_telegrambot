"""Base storage interface for application state management."""
from abc import ABC, abstractmethod
from typing import Optional, List

from models import UserSession, RunningReservation, PaymentStatus


class StorageInterface(ABC):
    """Abstract interface for application state storage."""

    # User Session Management
    @abstractmethod
    def get_user_session(self, chat_id: int) -> Optional[UserSession]:
        """Get user session by chat ID."""
        pass

    @abstractmethod
    def save_user_session(self, session: UserSession) -> None:
        """Save or update user session."""
        pass

    @abstractmethod
    def delete_user_session(self, chat_id: int) -> None:
        """Delete user session."""
        pass

    @abstractmethod
    def get_all_user_sessions(self) -> List[UserSession]:
        """Get all user sessions."""
        pass

    # Running Reservation Management
    @abstractmethod
    def get_running_reservation(self, chat_id: int) -> Optional[RunningReservation]:
        """Get running reservation by chat ID."""
        pass

    @abstractmethod
    def save_running_reservation(self, reservation: RunningReservation) -> None:
        """Save running reservation."""
        pass

    @abstractmethod
    def delete_running_reservation(self, chat_id: int) -> None:
        """Delete running reservation."""
        pass

    @abstractmethod
    def get_all_running_reservations(self) -> List[RunningReservation]:
        """Get all running reservations."""
        pass

    # Payment Status Management
    @abstractmethod
    def get_payment_status(self, chat_id: int) -> Optional[PaymentStatus]:
        """Get payment status by chat ID."""
        pass

    @abstractmethod
    def save_payment_status(self, status: PaymentStatus) -> None:
        """Save payment status."""
        pass

    @abstractmethod
    def delete_payment_status(self, chat_id: int) -> None:
        """Delete payment status."""
        pass

    # Subscriber Management
    @abstractmethod
    def add_subscriber(self, chat_id: int) -> None:
        """Add a subscriber for notifications."""
        pass

    @abstractmethod
    def remove_subscriber(self, chat_id: int) -> None:
        """Remove a subscriber."""
        pass

    @abstractmethod
    def get_all_subscribers(self) -> List[int]:
        """Get all subscriber chat IDs."""
        pass

    @abstractmethod
    def is_subscriber(self, chat_id: int) -> bool:
        """Check if chat ID is a subscriber."""
        pass

    # Admin Session Management
    @abstractmethod
    def is_admin_authenticated(self, chat_id: int) -> bool:
        """Check if chat ID is authenticated as admin."""
        pass

    @abstractmethod
    def set_admin_authenticated(self, chat_id: int, authenticated: bool = True) -> None:
        """Set admin authentication status for chat ID."""
        pass
