"""Unit tests for KorailService error mapping on top of pykorail (no network)."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pykorail.exceptions import (
    AccessRestrictedError,
    HttpStatusError,
    KorailError,
    LoginFailedError,
    NeedToLoginError,
    NoResultsError,
    PastDepartureError,
    SoldOutError,
)

from services.korail_service import KorailAccessRestrictedError, KorailService, TrainType


def _train(dep_time: str):
    train = MagicMock()
    train.dep_time = dep_time
    train.__str__ = lambda self: f"train@{dep_time}"
    return train


@pytest.fixture
def service(monkeypatch):
    """KorailService wired to a fake pykorail client."""
    svc = KorailService()
    fake = MagicMock()
    svc._korail_instance = fake
    svc._logged_in = True
    svc._username, svc._password = "010-0000-0000", "pw"
    return svc, fake


class TestLogin:
    def test_login_success(self, monkeypatch):
        svc = KorailService()
        fake = MagicMock()
        monkeypatch.setattr(svc, "_instance", lambda: fake)
        assert svc.login("010-0000-0000", "pw") is True
        fake.login.assert_called_once_with("010-0000-0000", "pw")
        assert svc.is_logged_in and svc.last_login_error is None

    @pytest.mark.parametrize(
        "exc, fragment",
        [
            (LoginFailedError("비밀번호가 틀렸습니다", "WRT200320"), "비밀번호"),
            (AccessRestrictedError(403, "매크로 등 미허가 도구", "-2000"), "이용 제한"),
            (HttpStatusError(403, "VPN 또는 데이터센터", "-8202"), "VPN"),
        ],
    )
    def test_login_failure_keeps_server_reason(self, monkeypatch, exc, fragment):
        svc = KorailService()
        fake = MagicMock()
        fake.login.side_effect = exc
        monkeypatch.setattr(svc, "_instance", lambda: fake)
        assert svc.login("010-0000-0000", "pw") is False
        assert not svc.is_logged_in
        assert fragment in svc.last_login_error


class TestSearchTrains:
    def test_filters_by_max_dep_time_using_train_field(self, service):
        svc, fake = service
        fake.trains.search.return_value = [_train("094400"), _train("125000"), _train("130000")]
        trains = svc.search_trains("20261001", "서울", "부산", "090000", "1300", TrainType.KTX, 1, verbose=False)
        assert [t.dep_time for t in trains] == ["094400", "125000"]
        kwargs = fake.trains.search.call_args.kwargs
        assert kwargs["depart_after"] == datetime(2026, 10, 1, 9, 0, 0)
        assert kwargs["train_type"] == TrainType.KTX

    def test_no_results_is_empty_list(self, service):
        svc, fake = service
        fake.trains.search.side_effect = NoResultsError()
        assert svc.search_trains("20261001", "서울", "부산", verbose=False) == []

    def test_maintenance_error_is_transient(self, service):
        svc, fake = service
        fake.trains.search.side_effect = KorailError("서비스를 일시중지하오니", "S000")
        assert svc.search_trains("20261001", "서울", "부산", verbose=False) == []

    def test_past_departure_is_fatal_value_error(self, service):
        svc, fake = service
        fake.trains.search.side_effect = PastDepartureError(datetime(2020, 1, 1), datetime(2026, 10, 6))
        with pytest.raises(ValueError):
            svc.search_trains("20200101", "서울", "부산", verbose=False)

    @pytest.mark.parametrize(
        "exc",
        [AccessRestrictedError(403, "매크로", "-2000"), HttpStatusError(403, "VPN 또는 데이터센터", "-8202")],
    )
    def test_access_restriction_stops_the_loop(self, service, exc):
        svc, fake = service
        fake.trains.search.side_effect = exc
        with pytest.raises(KorailAccessRestrictedError):
            svc.search_trains("20261001", "서울", "부산", verbose=False)

    def test_session_expiry_triggers_relogin(self, service):
        svc, fake = service
        fake.trains.search.side_effect = NeedToLoginError(code="P058")
        assert svc.search_trains("20261001", "서울", "부산", verbose=False) == []
        fake.login.assert_called_once_with("010-0000-0000", "pw")
        assert svc.is_logged_in

    def test_relogin_failure_is_not_fatal_and_backs_off(self, service):
        svc, fake = service
        fake.trains.search.side_effect = NeedToLoginError(code="P058")
        fake.login.side_effect = LoginFailedError("점검 중", "S000")
        assert svc.search_trains("20261001", "서울", "부산", verbose=False) == []
        assert not svc.is_logged_in
        # second call within the backoff window must not hit the login endpoint again
        assert svc.search_trains("20261001", "서울", "부산", verbose=False) == []
        assert fake.login.call_count == 1


class TestReserveTrain:
    def test_sold_out_returns_none(self, service):
        svc, fake = service
        fake.reservations.create.side_effect = SoldOutError(code="ERR211161")
        assert svc.reserve_train(_train("090000")) is None

    def test_duplicate_reservation_marker(self, service):
        svc, fake = service
        fake.reservations.create.side_effect = KorailError("동일한 예약 내역이 존재합니다", "WRR800029")
        assert svc.reserve_train(_train("090000")) == "DUPLICATE"

    def test_success_returns_reservation(self, service):
        svc, fake = service
        reservation = MagicMock(rsv_id="123")
        fake.reservations.create.return_value = reservation
        assert svc.reserve_train(_train("090000"), passenger_count=2) is reservation
        passengers = fake.reservations.create.call_args.kwargs["passengers"]
        assert len(passengers) == 1 and passengers[0].count == 2

    def test_access_restriction_propagates(self, service):
        svc, fake = service
        fake.reservations.create.side_effect = AccessRestrictedError(403, "매크로", "-2000")
        with pytest.raises(KorailAccessRestrictedError):
            svc.reserve_train(_train("090000"))
