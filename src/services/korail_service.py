"""Korail API service wrapper.

Backed by `pykorail` (코레일+ 7.0.8 규격). The public surface used by the rest of
the app is kept stable:

- ``login(username, password) -> bool``
- ``search_trains(...) -> list``
- ``reserve_train(...) -> reservation | None | "DUPLICATE"``
- ``search_and_reserve_loop(...)``
- ``is_logged_in``, ``_search_interval``
"""
import json
import os
import time
from datetime import datetime
from typing import Optional, List

from pykorail import Korail, TrainType, ReserveOption, AdultPassenger
from pykorail.device import profile_by_id, random_profile
from pykorail.exceptions import (
    AccessRestrictedError,
    HttpStatusError,
    KorailError,
    LoginFailedError,
    NeedToLoginError,
    NoResultsError,
    PastDepartureError,
    SoldOutError,
    StationNotFoundError,
    TransportError,
)

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "KorailService",
    "DuplicateReservationError",
    "KorailAccessRestrictedError",
    "TrainType",
    "ReserveOption",
]


class DuplicateReservationError(Exception):
    """Raised when attempting to reserve a train that's already reserved."""


class KorailAccessRestrictedError(Exception):
    """Korail refused the request because of the client environment (IP/VPN/anti-macro).

    Retrying from the same network only extends the block, so callers should stop
    the search loop and tell the user.
    """


class MultiReservationResult:
    """Container for several single-seat reservations made in random mode.

    pykorail's ``Reservation`` is a frozen dataclass, so metadata cannot be attached
    to it directly. This wrapper exposes the first reservation's attributes and the
    markers the background process looks for.
    """

    def __init__(self, reservations: List, total_seats: int):
        self._all_reservations = list(reservations)
        self._is_random_allocation = True
        self._total_seats = total_seats

    @property
    def first(self):
        return self._all_reservations[0]

    def __getattr__(self, name):
        return getattr(self.first, name)

    def __str__(self):
        return str(self.first)

    def __repr__(self):
        return repr(self.first)


def _load_device_profile():
    """Return a stable DynaPath device identity.

    Priority: explicit env (``KORAIL_DEVICE_PROFILE_ID`` + ``KORAIL_ANDROID_ID``),
    then the JSON file at ``KORAIL_DEVICE_FILE``, then a freshly generated profile
    which is persisted to that file so every process (web app, background
    reservation processes) presents the same device.
    """
    profile_id = settings.KORAIL_DEVICE_PROFILE_ID
    android_id = settings.KORAIL_ANDROID_ID
    if profile_id and android_id:
        try:
            profile = profile_by_id(profile_id, android_id=android_id)
            if profile:
                return profile
            logger.warning(f"Unknown KORAIL_DEVICE_PROFILE_ID '{profile_id}', falling back to file")
        except ValueError as e:
            logger.warning(f"Invalid device identity in environment: {e}")

    path = settings.KORAIL_DEVICE_FILE
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            profile = profile_by_id(saved.get("profile_id"), android_id=saved.get("android_id"))
            if profile:
                return profile
            logger.warning(f"Device file {path} holds an unknown profile, regenerating")
        except FileNotFoundError:
            pass
        except (ValueError, OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not read device file {path}: {e}")

    profile = random_profile()
    if path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"profile_id": profile.id, "android_id": profile.android_id}, f)
            logger.info(f"Generated new Korail device identity ({profile.id}) -> {path}")
        except OSError as e:
            logger.warning(f"Could not persist device identity to {path}: {e}")
    return profile


class KorailService:
    """Service for interacting with Korail API."""

    RELOGIN_RETRY_SECONDS = 60  # don't hammer the login endpoint while Korail is down

    def __init__(self):
        """Initialize Korail service."""
        self._korail_instance: Optional[Korail] = None
        self._logged_in = False
        self._search_interval = settings.KORAIL_SEARCH_INTERVAL
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._last_login_time: float = 0
        self._last_relogin_attempt: float = 0
        self._relogin_interval: int = 30 * 60  # 30 minutes
        self._relogin_count: int = 0
        self._device_profile = None
        self._last_login_payload: Optional[dict] = None
        self.last_login_error: Optional[str] = None

    # ------------------------------------------------------------------ login

    def _instance(self) -> Korail:
        if self._korail_instance is None:
            if self._device_profile is None:
                self._device_profile = _load_device_profile()
            self._korail_instance = Korail(device_profile=self._device_profile)
            self._hook_login_payload(self._korail_instance)
        return self._korail_instance

    def _hook_login_payload(self, korail: Korail) -> None:
        """Remember the raw login response.

        pykorail only exposes success/failure, but Korail piggybacks account notices on
        a successful login (e.g. WRC000420 "6개월 이상 동일한 비밀번호" with a
        ``strRedirectUrl``). While such a notice is pending the server keeps the session
        logged out (every authenticated call answers P058), so we need the text to tell
        the user what to do in the official app.
        """
        api = getattr(korail, "_api", None)
        if api is None or getattr(api, "_korail_service_hooked", False):
            return
        original_post = api.post

        def post(url, **kwargs):
            payload = original_post(url, **kwargs)
            if isinstance(payload, dict) and url.endswith("login.Login"):
                self._last_login_payload = payload
            return payload

        api.post = post
        api._korail_service_hooked = True

    def _login_notice(self) -> Optional[str]:
        """Server notice attached to the last login response, if any."""
        payload = self._last_login_payload or {}
        if payload.get("strRedirectUrl") or str(payload.get("h_msg_cd", "")).startswith("WRC"):
            text = (payload.get("h_msg_txt") or "").strip()
            return f"{text} ({payload.get('h_msg_cd')})" if text else str(payload.get("h_msg_cd"))
        return None

    def _verify_session(self, korail: Korail) -> bool:
        """Confirm the login produced a usable session with one cheap authenticated call."""
        try:
            korail.reservations.all()
            return True
        except NeedToLoginError:
            return False
        except Exception as e:  # network blip etc. — don't fail the login over it
            logger.debug(f"Session verification skipped: {type(e).__name__}: {e}")
            return True

    def login(self, username: str, password: str) -> bool:
        """
        Login to Korail with credentials.

        Args:
            username: Korail username (phone number 010-xxxx-xxxx, email or member no.)
            password: Korail password

        Returns:
            True if login successful, False otherwise. The server's reason is kept
            in ``last_login_error``.
        """
        self.last_login_error = None
        self._last_login_payload = None
        try:
            korail = self._instance()
            korail.login(username, password)
            notice = self._login_notice()
            if notice:
                logger.warning(f"Korail attached a notice to the login for {username}: {notice}")
            if not self._verify_session(korail):
                self.last_login_error = (
                    f"코레일 안내를 먼저 처리해야 합니다: {notice or '알 수 없는 안내'}\n"
                    f"코레일+ 앱에서 로그인해 안내를 확인(변경 또는 다음에 하기)한 뒤 다시 시도하세요."
                )
                logger.error(f"Korail login for {username} accepted but session is not usable: {notice}")
                self._logged_in = False
                return False
            self._logged_in = True
            self._username = username
            self._password = password
            self._last_login_time = time.time()
            logger.info(f"Korail login successful for user: {username}")
            return True
        except AccessRestrictedError as e:
            self.last_login_error = f"코레일 이용 제한: {e}"
            logger.error(f"Korail blocked this client (anti-macro) for user {username}: {e}")
        except HttpStatusError as e:
            self.last_login_error = str(e)  # e.g. "HTTP 403: VPN 또는 데이터센터... (-8202)"
            logger.error(f"Korail rejected login request for user {username}: {e}")
        except LoginFailedError as e:
            self.last_login_error = str(e)
            logger.warning(f"Korail login failed for user {username}: {e}")
        except TransportError as e:
            self.last_login_error = f"네트워크 오류: {e}"
            logger.error(f"Korail login transport error for user {username}: {e}")
        except Exception as e:
            self.last_login_error = f"{type(e).__name__}: {e}"
            logger.error(f"Korail login error for user {username}: {e}", exc_info=True)
        self._logged_in = False
        return False

    def _relogin(self) -> bool:
        """Re-login with stored credentials on the same device/session.

        Failures are not fatal: the search loop keeps running and retries later
        (``RELOGIN_RETRY_SECONDS``). Only an access restriction aborts.
        """
        if not self._username or not self._password:
            logger.error("🔒 Cannot re-login: no stored credentials")
            return False

        now = time.time()
        if now - self._last_relogin_attempt < self.RELOGIN_RETRY_SECONDS:
            return self._logged_in
        self._last_relogin_attempt = now

        logger.debug("🔄 Attempting re-login...")
        try:
            self._instance().login(self._username, self._password)
            self._logged_in = True
            self._last_login_time = now
            self._relogin_count += 1
            logger.debug(f"✅ Re-login successful (total: {self._relogin_count})")
            return True
        except AccessRestrictedError as e:
            raise KorailAccessRestrictedError(str(e)) from e
        except HttpStatusError as e:
            if getattr(e, "status_code", None) == 403:
                raise KorailAccessRestrictedError(str(e)) from e
            logger.error(f"❌ Re-login rejected by server, will retry later: {e}")
        except (LoginFailedError, TransportError) as e:
            logger.error(f"❌ Re-login failed, will retry later: {e}")
        except Exception as e:
            logger.error(f"❌ Re-login error, will retry later: {e}")
        self._logged_in = False
        return False

    def _check_session_refresh(self):
        """Proactively re-login if session is older than the relogin interval."""
        if not self._logged_in:
            self._relogin()
            return
        if self._last_login_time and (time.time() - self._last_login_time) >= self._relogin_interval:
            logger.debug(f"🔄 Session older than {self._relogin_interval}s, proactive re-login")
            self._relogin()

    # ----------------------------------------------------------------- search

    @staticmethod
    def _depart_after(dep_date: str, dep_time: str) -> datetime:
        return datetime.strptime(dep_date + (dep_time or "000000").ljust(6, "0")[:6], "%Y%m%d%H%M%S")

    def search_trains(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str = "000000",
        max_dep_time: str = "2400",
        train_type: str = TrainType.KTX,
        passenger_count: int = 1,
        verbose: bool = True
    ) -> List:
        """
        Search for trains with available seats.

        Args:
            dep_date: Departure date (YYYYMMDD)
            src_locate: Source station name (without '역')
            dst_locate: Destination station name (without '역')
            dep_time: Departure time (HHMMSS)
            max_dep_time: Maximum departure time threshold (HHMM)
            train_type: pykorail TrainType code
            passenger_count: Number of adult passengers

        Returns:
            List of trains (empty list when nothing is available or on a transient error)

        Raises:
            ValueError: Never logged in, bad station, or departure already passed
            KorailAccessRestrictedError: Korail blocked this client
        """
        if not self._korail_instance:
            raise ValueError("Must login before searching trains")
        if not self._logged_in and not self._relogin():
            return []

        passengers = [AdultPassenger(passenger_count)]
        if verbose:
            logger.debug(
                f"🔍 Searching {src_locate}→{dst_locate} {dep_date} {dep_time} "
                f"type={train_type} passengers={passenger_count} max_dep={max_dep_time}"
            )

        try:
            trains = self._korail_instance.trains.search(
                src_locate,
                dst_locate,
                depart_after=self._depart_after(dep_date, dep_time),
                train_type=train_type,
                passengers=passengers,
            )
        except NoResultsError:
            if verbose:
                logger.debug("No trains found for search criteria (NoResultsError)")
            return []
        except PastDepartureError as e:
            raise ValueError(f"출발 시각이 이미 지났습니다: {e}") from e
        except StationNotFoundError as e:
            raise ValueError(f"역 이름을 찾을 수 없습니다: {e}") from e
        except NeedToLoginError as e:
            logger.debug(f"🔒 Session expired during search, re-logging in: {e}")
            self._logged_in = False
            self._relogin()
            return []
        except AccessRestrictedError as e:
            raise KorailAccessRestrictedError(str(e)) from e
        except HttpStatusError as e:
            if getattr(e, "status_code", None) == 403:
                raise KorailAccessRestrictedError(str(e)) from e
            logger.error(f"❌ Korail HTTP error while searching: {e}")
            return []
        except KorailError as e:
            # e.g. S000 서비스 일시중지 (maintenance) — transient, keep looping
            logger.warning(f"⚠️ Korail returned an error while searching: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error searching trains: {type(e).__name__}: {e}")
            logger.debug("Search error traceback", exc_info=True)
            return []

        if verbose:
            logger.debug(f"📋 Korail API returned {len(trains)} trains")
            for i, train in enumerate(trains, 1):
                logger.debug(f"  Train #{i}: {train}")

        if trains and max_dep_time != "2400":
            max_time = int(max_dep_time)
            kept = []
            for train in trains:
                dep_time_int = self._extract_departure_time(train)
                if 0 < dep_time_int < max_time:
                    kept.append(train)
                elif verbose:
                    logger.debug(f"  ❌ Filtered out: {dep_time_int} >= {max_time}")
            trains = kept
            if verbose:
                logger.debug(f"📊 After max_dep_time filter: {len(trains)} trains remain")

        return trains

    # ---------------------------------------------------------------- reserve

    def reserve_train(
        self,
        train,
        option: str = ReserveOption.GENERAL_FIRST,
        passenger_count: int = 1
    ):
        """
        Attempt to reserve a specific train.

        Returns:
            Reservation object if successful, None otherwise.
            Returns "DUPLICATE" string if duplicate reservation detected.

        Raises:
            KorailAccessRestrictedError: Korail blocked this client
        """
        if not self._korail_instance:
            raise ValueError("Must login before reserving")
        if not self._logged_in and not self._relogin():
            logger.debug("Skipping reservation attempt: session not logged in (re-login pending)")
            return None

        passengers = [AdultPassenger(passenger_count)]
        logger.debug(f"🎫 Attempting reservation: {train} option={option} passengers={passenger_count}")

        try:
            reservation = self._korail_instance.reservations.create(
                train, passengers=passengers, option=option
            )
        except SoldOutError:
            logger.debug(f"Train sold out during reservation attempt: {train}")
            return None
        except NeedToLoginError as e:
            logger.debug(f"🔒 Session expired during reservation, re-logging in: {e}")
            self._logged_in = False
            self._relogin()
            return None
        except AccessRestrictedError as e:
            raise KorailAccessRestrictedError(str(e)) from e
        except HttpStatusError as e:
            if getattr(e, "status_code", None) == 403:
                raise KorailAccessRestrictedError(str(e)) from e
            logger.error(f"❌ Korail HTTP error while reserving: {e}")
            return None
        except KorailError as e:
            error_msg = str(e)
            code = getattr(e, "code", None)
            if "동일한 예약 내역" in error_msg or code == "WRR800029":
                logger.warning(f"⚠️ Duplicate reservation detected - will continue searching ({error_msg})")
                return "DUPLICATE"
            logger.error(f"❌ Reservation error ({code}): {error_msg} | train={train} option={option}")
            return None
        except Exception as e:
            logger.error(f"❌ Reservation error ({type(e).__name__}): {e} | train={train}", exc_info=True)
            return None

        if not reservation:
            logger.debug("Reservation returned None (no seats available)")
            return None

        logger.info("🎉 RESERVATION SUCCESS!")
        logger.info(f"  Reservation details: {reservation}")
        logger.info(f"  Reservation ID: {getattr(reservation, 'rsv_id', '?')}")
        return reservation

    # ------------------------------------------------------------------ loops

    def search_and_reserve_loop(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str = "000000",
        max_dep_time: str = "2400",
        train_type: str = TrainType.KTX,
        reserve_option: str = ReserveOption.GENERAL_FIRST,
        passenger_count: int = 1,
        seat_strategy: str = "consecutive",
        max_attempts: Optional[int] = None
    ):
        """
        Continuously search for trains and attempt reservation until successful.

        Returns:
            Reservation object(s) when successful, None if max_attempts reached
        """
        if not self._logged_in:
            raise ValueError("Must login before searching")

        logger.info(
            f"Starting reservation loop: {src_locate} -> {dst_locate} "
            f"on {dep_date} at {dep_time} for {passenger_count} passengers ({seat_strategy} seating)"
        )

        if seat_strategy == "consecutive":
            return self._search_and_reserve_consecutive(
                dep_date, src_locate, dst_locate, dep_time, max_dep_time,
                train_type, reserve_option, passenger_count, max_attempts
            )
        return self._search_and_reserve_random(
            dep_date, src_locate, dst_locate, dep_time, max_dep_time,
            train_type, reserve_option, passenger_count, max_attempts
        )

    def _search_and_reserve_consecutive(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str,
        max_dep_time: str,
        train_type: str,
        reserve_option: str,
        passenger_count: int,
        max_attempts: Optional[int]
    ):
        """Reserve seats consecutively (together)."""
        attempts = 0
        duplicate_notified = False

        logger.info(f"🔄 Starting consecutive seat search loop (passengers={passenger_count})")

        while True:
            attempts += 1
            if max_attempts and attempts > max_attempts:
                logger.warning(f"❌ Reached max attempts ({max_attempts}), stopping")
                return None

            if attempts % 1000 == 0:
                logger.info(f"📊 Search attempt #{attempts} (still searching..., re-logins: {self._relogin_count})")

            is_summary = (attempts % 60 == 0)
            if is_summary:
                logger.debug(f"━━━ Search attempt #{attempts} ━━━")

            self._check_session_refresh()

            trains = self.search_trains(
                dep_date, src_locate, dst_locate, dep_time, max_dep_time, train_type, passenger_count,
                verbose=is_summary
            )

            if not trains:
                if is_summary:
                    logger.debug(f"📊 Attempt #{attempts}: no trains found, retrying...")
                time.sleep(self._search_interval)
                continue

            for idx, train in enumerate(trains, 1):
                logger.debug(f"🚂 Trying train {idx}/{len(trains)}")
                reservation = self.reserve_train(train, option=reserve_option, passenger_count=passenger_count)

                if reservation == "DUPLICATE":
                    if not duplicate_notified:
                        duplicate_notified = True
                        logger.warning("⚠️ First duplicate detection - notifying user")
                        raise DuplicateReservationError("동일한 예약 내역이 존재합니다")
                    logger.debug("Duplicate reservation still exists, continuing search...")
                elif reservation:
                    logger.info(f"🎉 CONSECUTIVE RESERVATION SUCCESS after {attempts} attempts!")
                    return reservation
                else:
                    logger.debug(f"Train {idx} failed (sold out or unavailable)")

            logger.debug(f"All {len(trains)} trains sold out in attempt #{attempts}")
            time.sleep(self._search_interval)

    def _search_and_reserve_random(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str,
        max_dep_time: str,
        train_type: str,
        reserve_option: str,
        passenger_count: int,
        max_attempts: Optional[int]
    ):
        """Reserve seats randomly (one at a time until target count reached)."""
        attempts = 0
        reservations = []
        target_count = passenger_count
        duplicate_notified = False

        logger.info(f"Random seating: will reserve {target_count} individual tickets")

        while len(reservations) < target_count:
            attempts += 1
            if max_attempts and attempts > max_attempts:
                logger.warning(f"Reached max attempts ({max_attempts}), stopping")
                self._cancel_reservations(reservations)
                return None

            is_summary = (attempts % 60 == 0)

            self._check_session_refresh()

            trains = self.search_trains(
                dep_date, src_locate, dst_locate, dep_time, max_dep_time, train_type, passenger_count=1,
                verbose=is_summary
            )

            if not trains:
                if is_summary:
                    logger.debug(f"📊 Attempt #{attempts}: no trains found, retrying...")
                time.sleep(self._search_interval)
                continue

            for train in trains:
                logger.debug(
                    f"Found train: {train}, attempting reservation "
                    f"({len(reservations) + 1}/{target_count})..."
                )
                reservation = self.reserve_train(train, option=reserve_option, passenger_count=1)

                if reservation == "DUPLICATE":
                    if not duplicate_notified:
                        duplicate_notified = True
                        logger.warning("First duplicate detection - notifying user")
                        raise DuplicateReservationError("동일한 예약 내역이 존재합니다")
                    logger.debug("Duplicate reservation still exists, continuing search...")
                elif reservation:
                    reservations.append(reservation)
                    logger.info(f"Reserved seat {len(reservations)}/{target_count} (attempt #{attempts})")
                    logger.debug(f"Reservation details: {reservation}")

                    if len(reservations) >= target_count:
                        logger.info(f"All {target_count} seats reserved successfully! Total attempts: {attempts}")
                        return MultiReservationResult(reservations, target_count)

                    time.sleep(self._search_interval * 1.5)
                    break
                else:
                    logger.debug("Reservation failed, continuing search...")

            time.sleep(self._search_interval)

        return MultiReservationResult(reservations, target_count) if reservations else None

    def _cancel_reservations(self, reservations: List) -> None:
        """Cancel a list of reservations (cleanup for failed random allocation)."""
        if not reservations or not self._korail_instance:
            return

        logger.warning(f"Cancelling {len(reservations)} partial reservations...")
        for reservation in reservations:
            try:
                self._korail_instance.reservations.cancel(reservation)
                logger.warning(f"Cancelled reservation: {reservation}")
            except Exception as e:
                logger.error(f"Failed to cancel reservation {reservation}: {e}")

    @staticmethod
    def _extract_departure_time(train) -> int:
        """Departure time of a train as HHMM integer (0 if unknown)."""
        dep_time = getattr(train, "dep_time", "") or ""
        if len(dep_time) >= 4 and dep_time[:4].isdigit():
            return int(dep_time[:4])
        logger.error(f"Failed to extract departure time from train: {train}")
        return 0

    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._logged_in
