"""Reservation data models."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
