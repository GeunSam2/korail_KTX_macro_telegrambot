"""Input validation utilities."""
import re
from datetime import datetime
from typing import Tuple, Optional


class InputValidator:
    """Validator for user inputs in the reservation flow."""

    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Korean phone number format.

        Args:
            phone: Phone number string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return False, "전화번호를 입력해주세요."

        if "-" not in phone:
            return False, "'-'를 포함한 전화번호를 입력해주세요."

        # Pattern: 010-xxxx-xxxx or 01x-xxx-xxxx or 01x-xxxx-xxxx
        pattern = r'^01[0-9]-\d{3,4}-\d{4}$'
        if not re.match(pattern, phone):
            return False, "올바른 전화번호 형식이 아닙니다. (예: 010-1234-5678)"

        return True, None

    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate date in YYYYMMDD format.

        Args:
            date_str: Date string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not date_str:
            return False, "날짜를 입력해주세요."

        if not date_str.isdigit() or len(date_str) != 8:
            return False, "날짜 형식이 올바르지 않습니다. (예: 20230101)"

        # Check if date is valid
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            datetime(year, month, day)
        except ValueError:
            return False, "유효하지 않은 날짜입니다."

        # Check if date is not in the past
        today = datetime.today().strftime("%Y%m%d")
        if date_str < today:
            return False, "과거 날짜는 선택할 수 없습니다."

        return True, None

    @staticmethod
    def validate_time(time_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate time in HHMM format.

        Args:
            time_str: Time string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not time_str:
            return False, "시간을 입력해주세요."

        if not time_str.isdigit() or len(time_str) != 4:
            return False, "시간 형식이 올바르지 않습니다. (예: 1430)"

        hours = int(time_str[:2])
        minutes = int(time_str[2:4])

        if hours > 23:
            return False, "시간은 0-23 사이여야 합니다."

        if minutes > 59:
            return False, "분은 0-59 사이여야 합니다."

        return True, None

    @staticmethod
    def validate_station_name(station: str) -> Tuple[bool, Optional[str]]:
        """
        Validate station name.

        Args:
            station: Station name

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not station:
            return False, "역 이름을 입력해주세요."

        if "역" in station:
            return False, "'역'을 제외한 이름을 입력해주세요. (예: 광명)"

        # Check minimum length
        if len(station) < 2:
            return False, "역 이름이 너무 짧습니다."

        return True, None

    @staticmethod
    def validate_yes_no(answer: str) -> Tuple[bool, Optional[str]]:
        """
        Validate yes/no answer.

        Args:
            answer: User's answer

        Returns:
            Tuple of (is_yes, None) or (False, error_message)
        """
        answer = answer.strip().upper()

        if answer in ["Y", "예", "YES"]:
            return True, None
        elif answer in ["N", "아니오", "NO"]:
            return False, None
        else:
            return None, "Y/예 또는 N/아니오를 입력해주세요."

    @staticmethod
    def validate_train_type_choice(choice: str) -> Tuple[bool, Optional[str]]:
        """
        Validate train type choice (1 or 2).

        Args:
            choice: User's choice

        Returns:
            Tuple of (is_valid, error_message)
        """
        if choice not in ["1", "2"]:
            return False, "1 또는 2를 입력해주세요."

        return True, None

    @staticmethod
    def validate_special_option_choice(choice: str) -> Tuple[bool, Optional[str]]:
        """
        Validate special seat option choice (1, 2, 3, or 4).

        Args:
            choice: User's choice

        Returns:
            Tuple of (is_valid, error_message)
        """
        if choice not in ["1", "2", "3", "4"]:
            return False, "1, 2, 3, 4 중 하나를 선택해주세요."

        return True, None
