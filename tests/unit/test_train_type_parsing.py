"""Unit tests for train type parsing in background process."""
import sys
sys.path.insert(0, '/Users/gray/dev/geunsam2/korail_KTX_macro_telegrambot/src')

from korail2 import TrainType, ReserveOption


class MockBackgroundProcess:
    """Mock class to test parsing methods."""

    def _parse_train_type(self, train_type_str: str) -> TrainType:
        """Parse train type from string."""
        # Check for exact string representation of enum
        if "TrainType.KTX" in train_type_str:
            return TrainType.KTX
        elif "TrainType.ALL" in train_type_str:
            return TrainType.ALL
        # Fallback to checking for keywords
        elif "KTX" in train_type_str.upper() and "ALL" not in train_type_str.upper():
            return TrainType.KTX
        else:
            return TrainType.ALL

    def _parse_reserve_option(self, option_str: str) -> ReserveOption:
        """Parse reserve option from string."""
        # Check for exact string representation of enum
        if "ReserveOption.GENERAL_FIRST" in option_str:
            return ReserveOption.GENERAL_FIRST
        elif "ReserveOption.GENERAL_ONLY" in option_str:
            return ReserveOption.GENERAL_ONLY
        elif "ReserveOption.SPECIAL_FIRST" in option_str:
            return ReserveOption.SPECIAL_FIRST
        elif "ReserveOption.SPECIAL_ONLY" in option_str:
            return ReserveOption.SPECIAL_ONLY

        # Fallback to checking for keywords
        option_str_upper = option_str.upper()
        if "GENERAL_FIRST" in option_str_upper:
            return ReserveOption.GENERAL_FIRST
        elif "GENERAL_ONLY" in option_str_upper:
            return ReserveOption.GENERAL_ONLY
        elif "SPECIAL_FIRST" in option_str_upper:
            return ReserveOption.SPECIAL_FIRST
        elif "SPECIAL_ONLY" in option_str_upper:
            return ReserveOption.SPECIAL_ONLY
        else:
            return ReserveOption.GENERAL_FIRST


def test_parse_train_type_ktx_enum():
    """Test parsing TrainType.KTX string representation."""
    process = MockBackgroundProcess()
    result = process._parse_train_type("TrainType.KTX")
    assert result == TrainType.KTX


def test_parse_train_type_all_enum():
    """Test parsing TrainType.ALL string representation."""
    process = MockBackgroundProcess()
    result = process._parse_train_type("TrainType.ALL")
    assert result == TrainType.ALL


def test_parse_train_type_ktx_keyword():
    """Test parsing 'KTX' keyword."""
    process = MockBackgroundProcess()
    result = process._parse_train_type("KTX")
    assert result == TrainType.KTX


def test_parse_train_type_all_keyword():
    """Test parsing 'ALL' keyword."""
    process = MockBackgroundProcess()
    result = process._parse_train_type("ALL")
    assert result == TrainType.ALL


def test_parse_reserve_option_general_first():
    """Test parsing GENERAL_FIRST option."""
    process = MockBackgroundProcess()
    result = process._parse_reserve_option("ReserveOption.GENERAL_FIRST")
    assert result == ReserveOption.GENERAL_FIRST


def test_parse_reserve_option_general_only():
    """Test parsing GENERAL_ONLY option."""
    process = MockBackgroundProcess()
    result = process._parse_reserve_option("ReserveOption.GENERAL_ONLY")
    assert result == ReserveOption.GENERAL_ONLY


def test_parse_reserve_option_special_first():
    """Test parsing SPECIAL_FIRST option."""
    process = MockBackgroundProcess()
    result = process._parse_reserve_option("ReserveOption.SPECIAL_FIRST")
    assert result == ReserveOption.SPECIAL_FIRST


def test_parse_reserve_option_special_only():
    """Test parsing SPECIAL_ONLY option."""
    process = MockBackgroundProcess()
    result = process._parse_reserve_option("ReserveOption.SPECIAL_ONLY")
    assert result == ReserveOption.SPECIAL_ONLY
