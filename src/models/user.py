"""User data models."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserCredentials:
    """Korail login credentials."""
    korail_id: str  # Phone number format: 010-xxxx-xxxx
    korail_pw: str


@dataclass
class UserSession:
    """User session data for conversation flow."""
    chat_id: int
    in_progress: bool = False
    last_action: int = 0  # Progress state (0-12)
    credentials: Optional[UserCredentials] = None
    train_info: dict = field(default_factory=dict)
    process_id: int = 9999999  # PID of background reservation process

    def reset(self) -> None:
        """Reset user session to initial state."""
        self.in_progress = False
        self.last_action = 0
        self.train_info = {}
        self.process_id = 9999999


@dataclass
class UserProgress:
    """Represents user's progress in the reservation flow."""

    # Progress state constants
    INIT = 0
    STARTED = 1
    START_ACCEPTED = 2
    ID_INPUT_SUCCESS = 3
    PW_INPUT_SUCCESS = 4
    DATE_INPUT_SUCCESS = 5
    SRC_LOCATE_INPUT_SUCCESS = 6
    DST_LOCATE_INPUT_SUCCESS = 7
    DEP_TIME_INPUT_SUCCESS = 8
    MAX_DEP_TIME_INPUT_SUCCESS = 9
    TRAIN_TYPE_INPUT_SUCCESS = 10
    SPECIAL_INPUT_SUCCESS = 11
    FINDING_TICKET = 12
