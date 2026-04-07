"""Reservation data models."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List


@dataclass
class TrainSearchParams:
    """Parameters for searching trains."""
    dep_date: str  # Format: YYYYMMDD
    src_locate: str  # Station name (without '역')
    dst_locate: str  # Station name (without '역')
    dep_time: str  # Format: HHMMSS
    max_dep_time: str = "2400"  # Format: HHMM
    train_type: str = "TrainType.KTX"  # korail2.TrainType enum as string
    train_type_display: str = "KTX"
    special_option: str = "ReserveOption.GENERAL_FIRST"  # korail2.ReserveOption enum as string
    special_option_display: str = "GENERAL_FIRST"
    passenger_count: int = 1  # Number of adult passengers (1-9)
    seat_strategy: str = "consecutive"  # "consecutive" or "random"

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate search parameters.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate date format
        if not self.dep_date.isdigit() or len(self.dep_date) != 8:
            return False, "날짜 형식이 올바르지 않습니다 (YYYYMMDD)"

        # Validate date is not in the past
        today = datetime.today().strftime("%Y%m%d")
        if self.dep_date < today:
            return False, "과거 날짜는 선택할 수 없습니다"

        # Validate time format
        if not self.dep_time[:4].isdigit() or len(self.dep_time) != 6:
            return False, "시간 형식이 올바르지 않습니다 (HHMMSS)"

        return True, None


@dataclass
class RunningReservation:
    """Information about a running reservation process."""
    chat_id: int
    process_id: int
    korail_id: str
    search_params: TrainSearchParams
    started_at: datetime = datetime.now()


@dataclass
class PaymentStatus:
    """Payment completion status for a reservation."""
    chat_id: int
    completed: bool = False
    reservation_time: Optional[datetime] = None
    reminder_active: bool = False


class ReservationPaymentStatus(Enum):
    """Payment status for individual reservations."""
    PENDING = "pending"      # Reservation made, awaiting payment
    PAID = "paid"           # Payment completed by user
    EXPIRED = "expired"     # Reservation expired due to timeout
    CANCELLED = "cancelled" # Manually cancelled by user


@dataclass
class SingleReservationInfo:
    """Information about a single train reservation."""
    reservation_id: str              # Unique ID from korail2
    reservation_obj: any             # Original reservation object from korail2
    reserved_at: datetime            # When reservation was created
    expires_at: datetime             # When reservation will expire
    status: ReservationPaymentStatus # Current payment status
    seat_number: int                 # Seat number in the group (1, 2, 3...)
    train_info: str                  # Human-readable train info for display

    def get_remaining_seconds(self) -> int:
        """Get remaining seconds until expiration."""
        if self.status != ReservationPaymentStatus.PENDING:
            return 0

        now = datetime.now()
        if now >= self.expires_at:
            return 0

        return int((self.expires_at - now).total_seconds())

    def get_remaining_minutes_display(self) -> str:
        """Get human-readable remaining time (e.g., '8분 30초')."""
        remaining = self.get_remaining_seconds()
        if remaining <= 0:
            return "만료됨"

        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes}분 {seconds}초"

    def is_expired(self) -> bool:
        """Check if reservation has expired."""
        return datetime.now() >= self.expires_at


@dataclass
class MultiReservationStatus:
    """Status tracking for multiple reservations in random seat allocation."""
    chat_id: int
    reservations: List[SingleReservationInfo]
    total_seats: int
    seat_strategy: str  # "random" or "consecutive"
    created_at: datetime
    manually_stopped: bool = False  # True if user manually stopped reminders

    def get_pending_count(self) -> int:
        """Count how many reservations are still pending payment."""
        return sum(1 for r in self.reservations
                  if r.status == ReservationPaymentStatus.PENDING and not r.is_expired())

    def get_paid_count(self) -> int:
        """Count how many reservations have been paid."""
        return sum(1 for r in self.reservations
                  if r.status == ReservationPaymentStatus.PAID)

    def get_expired_count(self) -> int:
        """Count how many reservations have expired."""
        return sum(1 for r in self.reservations
                  if r.status == ReservationPaymentStatus.EXPIRED or r.is_expired())

    def should_show_reminder(self) -> bool:
        """Determine if reminder should be shown."""
        # Don't show if manually stopped
        if self.manually_stopped:
            return False

        # Show only if there are pending reservations that haven't expired
        return self.get_pending_count() > 0

    def get_most_urgent_reservation(self) -> Optional[SingleReservationInfo]:
        """Get the reservation with least time remaining (most urgent)."""
        pending = [r for r in self.reservations
                  if r.status == ReservationPaymentStatus.PENDING and not r.is_expired()]

        if not pending:
            return None

        # Return the one with earliest expiration time
        return min(pending, key=lambda r: r.expires_at)

    def mark_all_expired(self) -> None:
        """Mark all pending reservations as expired."""
        for reservation in self.reservations:
            if reservation.status == ReservationPaymentStatus.PENDING:
                reservation.status = ReservationPaymentStatus.EXPIRED

    def mark_reservation_paid(self, seat_number: int) -> bool:
        """Mark a specific reservation as paid."""
        for reservation in self.reservations:
            if reservation.seat_number == seat_number:
                reservation.status = ReservationPaymentStatus.PAID
                return True
        return False
