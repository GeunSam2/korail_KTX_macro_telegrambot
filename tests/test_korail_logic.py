"""
Korail 예약 로직 단위 테스트
korail2 라이브러리와 예약 관련 로직이 제대로 import되고 기본 구조가 유효한지 테스트합니다.
"""
import pytest
import sys
import os

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_korail2_import():
    """
    korail2 라이브러리가 제대로 설치되고 import되는지 확인

    dhfhfk/korail2 bypassDynapath 브랜치가 제대로 설치되어야 합니다.
    """
    try:
        import korail2
        assert korail2 is not None
    except ImportError as e:
        pytest.fail(f"korail2 import 실패: {e}")


def test_korail2_classes():
    """
    korail2의 주요 클래스들이 import되는지 확인
    """
    try:
        from korail2 import Korail, TrainType, ReserveOption
        assert Korail is not None
        assert TrainType is not None
        assert ReserveOption is not None
    except ImportError as e:
        pytest.fail(f"korail2 클래스 import 실패: {e}")


def test_korail_reserve_module_import():
    """
    korailReserve 모듈이 제대로 import되는지 확인
    """
    try:
        from telegramBot import korailReserve
        assert korailReserve is not None
    except ImportError as e:
        pytest.fail(f"korailReserve 모듈 import 실패: {e}")


def test_telegram_bot_dependencies():
    """
    python-telegram-bot 라이브러리가 제대로 설치되어 있는지 확인
    """
    try:
        import telegram
        assert telegram is not None
    except ImportError as e:
        pytest.fail(f"python-telegram-bot import 실패: {e}")


def test_flask_dependencies():
    """
    Flask 관련 의존성들이 제대로 설치되어 있는지 확인
    """
    try:
        import flask
        import flask_restful
        import flask_cors
        assert flask is not None
        assert flask_restful is not None
        assert flask_cors is not None
    except ImportError as e:
        pytest.fail(f"Flask 의존성 import 실패: {e}")


def test_payment_reminder_time_constants():
    """
    결제 리마인더 시간 설정이 10분(600초)인지 확인

    최근 변경사항: 20분 → 10분으로 변경
    """
    from telegramBot.korailReserve import Korail

    # korailReserve.py의 sendPaymentReminders 메서드 확인
    import inspect
    source = inspect.getsource(Korail.sendPaymentReminders)

    # 10분 = 600초 확인
    assert '10 * 60' in source or '600' in source, "결제 시간이 10분으로 설정되어야 합니다"
    # 10초 간격 확인
    assert 'interval = 10' in source or 'interval=10' in source, "리마인더 간격이 10초로 설정되어야 합니다"
