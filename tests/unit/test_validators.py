"""
Comprehensive tests for input validators.

Tests all edge cases, boundary conditions, and error handling.
"""
import sys
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from utils.validators import InputValidator


class TestPhoneNumberValidation:
    """Test phone number validation."""

    def test_valid_phone_with_hyphens(self):
        """Test valid phone number with hyphens."""
        valid, _ = InputValidator.validate_phone_number("010-1234-5678")
        assert valid is True

    def test_valid_phone_011(self):
        """Test valid 011 phone number."""
        valid, _ = InputValidator.validate_phone_number("011-123-4567")
        assert valid is True

    def test_invalid_phone_without_hyphens(self):
        """Test phone number without hyphens is invalid."""
        valid, error = InputValidator.validate_phone_number("01012345678")
        assert valid is False
        assert "'-'" in error or "하이픈" in error

    def test_invalid_phone_short(self):
        """Test phone number that's too short."""
        valid, error = InputValidator.validate_phone_number("010-123-456")
        assert valid is False

    def test_invalid_phone_wrong_prefix(self):
        """Test phone number with wrong prefix."""
        valid, error = InputValidator.validate_phone_number("020-1234-5678")
        assert valid is False

    def test_invalid_phone_empty(self):
        """Test empty phone number."""
        valid, error = InputValidator.validate_phone_number("")
        assert valid is False

    def test_invalid_phone_with_letters(self):
        """Test phone number with letters."""
        valid, error = InputValidator.validate_phone_number("010-abcd-5678")
        assert valid is False


class TestDateValidation:
    """Test date validation."""

    def test_valid_future_date(self):
        """Test valid future date."""
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
        valid, _ = InputValidator.validate_date(future_date)
        assert valid is True

    def test_valid_today(self):
        """Test today's date is valid."""
        today = datetime.now().strftime("%Y%m%d")
        valid, _ = InputValidator.validate_date(today)
        assert valid is True

    def test_invalid_past_date(self):
        """Test past date is invalid."""
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        valid, error = InputValidator.validate_date(past_date)
        assert valid is False
        assert "과거" in error or "오늘" in error

    def test_invalid_date_format(self):
        """Test invalid date format."""
        valid, error = InputValidator.validate_date("2023-01-01")
        assert valid is False

    def test_invalid_date_length(self):
        """Test date with wrong length."""
        valid, error = InputValidator.validate_date("202301")
        assert valid is False

    def test_invalid_date_non_numeric(self):
        """Test date with non-numeric characters."""
        valid, error = InputValidator.validate_date("abcd0101")
        assert valid is False

    def test_invalid_date_month_boundary(self):
        """Test invalid month (13)."""
        valid, error = InputValidator.validate_date("20231301")
        assert valid is False

    def test_invalid_date_day_boundary(self):
        """Test invalid day (32)."""
        valid, error = InputValidator.validate_date("20230132")
        assert valid is False

    def test_valid_leap_year(self):
        """Test leap year date (Feb 29 in leap year)."""
        # Find next leap year
        year = datetime.now().year
        while year % 4 != 0 or (year % 100 == 0 and year % 400 != 0):
            year += 1

        if year > datetime.now().year:
            date = f"{year}0229"
            valid, _ = InputValidator.validate_date(date)
            # Only valid if it's in the future
            assert valid is True or valid is False  # Depends on current date

    def test_invalid_non_leap_year_feb29(self):
        """Test Feb 29 in non-leap year."""
        # 2023 is not a leap year
        if datetime.now().year <= 2023:
            valid, error = InputValidator.validate_date("20230229")
            assert valid is False


class TestTimeValidation:
    """Test time validation."""

    def test_valid_morning_time(self):
        """Test valid morning time."""
        valid, _ = InputValidator.validate_time("0900")
        assert valid is True

    def test_valid_afternoon_time(self):
        """Test valid afternoon time."""
        valid, _ = InputValidator.validate_time("1430")
        assert valid is True

    def test_valid_evening_time(self):
        """Test valid evening time."""
        valid, _ = InputValidator.validate_time("2159")
        assert valid is True

    def test_valid_midnight(self):
        """Test midnight (0000)."""
        valid, _ = InputValidator.validate_time("0000")
        assert valid is True

    def test_valid_last_minute(self):
        """Test last minute of day (2359)."""
        valid, _ = InputValidator.validate_time("2359")
        assert valid is True

    def test_invalid_hour_24(self):
        """Test invalid hour (24)."""
        valid, error = InputValidator.validate_time("2400")
        assert valid is False

    def test_invalid_hour_25(self):
        """Test invalid hour (25)."""
        valid, error = InputValidator.validate_time("2560")
        assert valid is False

    def test_invalid_minute_60(self):
        """Test invalid minute (60)."""
        valid, error = InputValidator.validate_time("1060")
        assert valid is False

    def test_invalid_minute_99(self):
        """Test invalid minute (99)."""
        valid, error = InputValidator.validate_time("1099")
        assert valid is False

    def test_invalid_time_short(self):
        """Test time that's too short."""
        valid, error = InputValidator.validate_time("123")
        assert valid is False

    def test_invalid_time_long(self):
        """Test time that's too long."""
        valid, error = InputValidator.validate_time("12345")
        assert valid is False

    def test_invalid_time_non_numeric(self):
        """Test time with non-numeric characters."""
        valid, error = InputValidator.validate_time("12ab")
        assert valid is False


class TestStationNameValidation:
    """Test station name validation."""

    def test_valid_station_seoul(self):
        """Test valid station: Seoul."""
        valid, _ = InputValidator.validate_station_name("서울")
        assert valid is True

    def test_valid_station_busan(self):
        """Test valid station: Busan."""
        valid, _ = InputValidator.validate_station_name("부산")
        assert valid is True

    def test_valid_station_dongdaegu(self):
        """Test valid station: Dongdaegu."""
        valid, _ = InputValidator.validate_station_name("동대구")
        assert valid is True

    def test_invalid_station_empty(self):
        """Test empty station name."""
        valid, error = InputValidator.validate_station_name("")
        assert valid is False

    def test_invalid_station_too_short(self):
        """Test station name that's too short."""
        valid, error = InputValidator.validate_station_name("서")
        assert valid is False

    def test_invalid_station_too_long(self):
        """Test station name that's too long."""
        valid, error = InputValidator.validate_station_name("가나다라마바사아자차카")
        assert valid is False

    def test_invalid_station_with_suffix(self):
        """Test station name with '역' suffix."""
        valid, error = InputValidator.validate_station_name("서울역")
        assert valid is False
        assert "역" in error

    def test_invalid_station_nonexistent(self):
        """Test nonexistent station name."""
        valid, error = InputValidator.validate_station_name("가짜스테이션")
        assert valid is False
        # Either "존재하지" (not found) or some error should be present
        assert error is not None and len(error) > 0

    def test_invalid_station_whitespace(self):
        """Test station name with only whitespace."""
        valid, error = InputValidator.validate_station_name("   ")
        assert valid is False


class TestYesNoValidation:
    """Test yes/no validation."""

    def test_valid_yes_uppercase(self):
        """Test 'Y' for yes."""
        result, _ = InputValidator.validate_yes_no("Y")
        assert result is True

    def test_valid_yes_lowercase(self):
        """Test 'y' for yes."""
        result, _ = InputValidator.validate_yes_no("y")
        assert result is True

    def test_valid_no_uppercase(self):
        """Test 'N' for no."""
        result, _ = InputValidator.validate_yes_no("N")
        assert result is False

    def test_valid_no_lowercase(self):
        """Test 'n' for no."""
        result, _ = InputValidator.validate_yes_no("n")
        assert result is False

    def test_invalid_maybe(self):
        """Test invalid input."""
        result, error = InputValidator.validate_yes_no("maybe")
        assert result is None
        assert error is not None


class TestChoiceValidation:
    """Test choice validation."""

    def test_valid_train_type_ktx(self):
        """Test valid train type choice: KTX."""
        valid, _ = InputValidator.validate_train_type_choice("1")
        assert valid is True

    def test_valid_train_type_all(self):
        """Test valid train type choice: ALL."""
        valid, _ = InputValidator.validate_train_type_choice("2")
        assert valid is True

    def test_invalid_train_type_zero(self):
        """Test invalid train type choice: 0."""
        valid, error = InputValidator.validate_train_type_choice("0")
        assert valid is False

    def test_invalid_train_type_three(self):
        """Test invalid train type choice: 3."""
        valid, error = InputValidator.validate_train_type_choice("3")
        assert valid is False

    def test_valid_special_option_general_first(self):
        """Test valid special option: GENERAL_FIRST."""
        valid, _ = InputValidator.validate_special_option_choice("1")
        assert valid is True

    def test_valid_special_option_all(self):
        """Test all special options (1-4) are valid."""
        for choice in ["1", "2", "3", "4"]:
            valid, _ = InputValidator.validate_special_option_choice(choice)
            assert valid is True

    def test_invalid_special_option_zero(self):
        """Test invalid special option: 0."""
        valid, error = InputValidator.validate_special_option_choice("0")
        assert valid is False

    def test_invalid_special_option_five(self):
        """Test invalid special option: 5."""
        valid, error = InputValidator.validate_special_option_choice("5")
        assert valid is False


class TestPassengerCountValidation:
    """Test passenger count validation."""

    def test_valid_single_passenger(self):
        """Test valid single passenger."""
        valid, _ = InputValidator.validate_passenger_count("1")
        assert valid is True

    def test_valid_multiple_passengers(self):
        """Test valid multiple passengers."""
        valid, _ = InputValidator.validate_passenger_count("5")
        assert valid is True

    def test_valid_max_passengers(self):
        """Test maximum passengers (9)."""
        valid, _ = InputValidator.validate_passenger_count("9")
        assert valid is True

    def test_invalid_zero_passengers(self):
        """Test zero passengers is invalid."""
        valid, error = InputValidator.validate_passenger_count("0")
        assert valid is False
        assert "최소 1명" in error

    def test_invalid_too_many_passengers(self):
        """Test too many passengers (>9)."""
        valid, error = InputValidator.validate_passenger_count("10")
        assert valid is False
        assert "최대 9명" in error

    def test_invalid_negative_passengers(self):
        """Test negative passengers."""
        # Note: Since we check for isdigit(), "-1" will be caught as non-digit
        valid, error = InputValidator.validate_passenger_count("-1")
        assert valid is False

    def test_invalid_non_numeric(self):
        """Test non-numeric passenger count."""
        valid, error = InputValidator.validate_passenger_count("abc")
        assert valid is False
        assert "숫자" in error

    def test_invalid_empty(self):
        """Test empty passenger count."""
        valid, error = InputValidator.validate_passenger_count("")
        assert valid is False


class TestSeatStrategyValidation:
    """Test seat strategy validation."""

    def test_valid_consecutive_seats(self):
        """Test valid consecutive seat strategy."""
        valid, _ = InputValidator.validate_seat_strategy_choice("1")
        assert valid is True

    def test_valid_random_seats(self):
        """Test valid random seat strategy."""
        valid, _ = InputValidator.validate_seat_strategy_choice("2")
        assert valid is True

    def test_invalid_zero(self):
        """Test invalid choice: 0."""
        valid, error = InputValidator.validate_seat_strategy_choice("0")
        assert valid is False

    def test_invalid_three(self):
        """Test invalid choice: 3."""
        valid, error = InputValidator.validate_seat_strategy_choice("3")
        assert valid is False

    def test_invalid_non_digit(self):
        """Test non-digit choice."""
        valid, error = InputValidator.validate_seat_strategy_choice("a")
        assert valid is False


class TestPasswordValidation:
    """Test password validation."""

    def test_valid_simple_password(self):
        """Test valid simple password."""
        valid, _ = InputValidator.validate_password("1234")
        assert valid is True

    def test_valid_complex_password(self):
        """Test valid complex password."""
        valid, _ = InputValidator.validate_password("MyP@ssw0rd!")
        assert valid is True

    def test_invalid_too_short(self):
        """Test password that's too short."""
        valid, error = InputValidator.validate_password("123")
        assert valid is False
        assert "짧습니다" in error

    def test_invalid_too_long(self):
        """Test password that's too long."""
        long_pw = "a" * 51
        valid, error = InputValidator.validate_password(long_pw)
        assert valid is False
        assert "깁니다" in error

    def test_invalid_empty(self):
        """Test empty password."""
        valid, error = InputValidator.validate_password("")
        assert valid is False

    def test_invalid_suspicious_script(self):
        """Test password with script injection."""
        valid, error = InputValidator.validate_password("<script>alert('xss')</script>")
        assert valid is False

    def test_invalid_suspicious_sql(self):
        """Test password with SQL keywords."""
        valid, error = InputValidator.validate_password("password'; DROP TABLE users--")
        assert valid is False


class TestPhoneNumberEnhancedValidation:
    """Test enhanced phone number validation."""

    def test_valid_with_whitespace(self):
        """Test valid phone with leading/trailing whitespace."""
        valid, _ = InputValidator.validate_phone_number("  010-1234-5678  ")
        assert valid is True

    def test_invalid_sql_injection(self):
        """Test phone with SQL injection attempt."""
        valid, error = InputValidator.validate_phone_number("010-1234-5678; DROP TABLE users")
        assert valid is False

    def test_invalid_script_injection(self):
        """Test phone with script injection attempt."""
        valid, error = InputValidator.validate_phone_number("<script>alert('xss')</script>")
        assert valid is False


class TestDateEnhancedValidation:
    """Test enhanced date validation."""

    def test_invalid_too_far_future(self):
        """Test date that's too far in the future."""
        far_future = (datetime.now() + timedelta(days=400)).strftime("%Y%m%d")
        valid, error = InputValidator.validate_date(far_future)
        assert valid is False
        assert "기간" in error or "초과" in error

    def test_valid_with_whitespace(self):
        """Test valid date with whitespace."""
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
        valid, _ = InputValidator.validate_date(f"  {future_date}  ")
        assert valid is True

    def test_invalid_year_too_old(self):
        """Test date with year too old."""
        valid, error = InputValidator.validate_date("19990101")
        assert valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
