"""Korail API service wrapper."""
import time
from typing import Optional, List
from korail2 import Korail as K2MKorail, TrainType, ReserveOption, SoldOutError, NoResultsError

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class KorailService:
    """Service for interacting with Korail API."""

    def __init__(self):
        """Initialize Korail service."""
        self._korail_instance: Optional[K2MKorail] = None
        self._logged_in = False
        self._search_interval = settings.KORAIL_SEARCH_INTERVAL

    def login(self, username: str, password: str) -> bool:
        """
        Login to Korail with credentials.

        Args:
            username: Korail username (phone number in format 010-xxxx-xxxx)
            password: Korail password

        Returns:
            True if login successful, False otherwise
        """
        try:
            self._korail_instance = K2MKorail(username, password, auto_login=False)
            self._logged_in = self._korail_instance.login()

            if self._logged_in:
                logger.info(f"Korail login successful for user: {username}")
            else:
                logger.warning(f"Korail login failed for user: {username}")

            return self._logged_in
        except Exception as e:
            logger.error(f"Korail login error for user {username}: {e}")
            return False

    def search_trains(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str = "000000",
        max_dep_time: str = "2400",
        train_type: TrainType = TrainType.KTX
    ) -> List:
        """
        Search for available trains.

        Args:
            dep_date: Departure date (YYYYMMDD)
            src_locate: Source station name (without '역')
            dst_locate: Destination station name (without '역')
            dep_time: Departure time (HHMMSS)
            max_dep_time: Maximum departure time threshold (HHMM)
            train_type: Type of train to search for

        Returns:
            List of available trains

        Raises:
            ValueError: If not logged in
        """
        if not self._logged_in or not self._korail_instance:
            raise ValueError("Must login before searching trains")

        try:
            trains = self._korail_instance.search_train(
                src_locate,
                dst_locate,
                dep_date,
                dep_time,
                train_type=train_type
            )

            # Filter by max departure time
            if trains and max_dep_time != "2400":
                time_str = "".join(str(trains[0]).split("(")[1].split("~")[0].split(":"))
                if int(time_str) >= int(max_dep_time):
                    trains = []

            logger.info(
                f"Found {len(trains)} trains from {src_locate} to {dst_locate} "
                f"on {dep_date} at {dep_time}"
            )
            return trains

        except NoResultsError:
            logger.debug(f"No trains found for search criteria")
            return []
        except Exception as e:
            logger.error(f"Error searching trains: {e}")
            return []

    def reserve_train(self, train, option: ReserveOption = ReserveOption.GENERAL_FIRST):
        """
        Attempt to reserve a specific train.

        Args:
            train: Train object from search_trains()
            option: Reservation option (special seat preference)

        Returns:
            Reservation object if successful, None otherwise
        """
        if not self._logged_in or not self._korail_instance:
            raise ValueError("Must login before reserving")

        try:
            logger.info(f"Attempting to reserve train: {train}")
            reservation = self._korail_instance.reserve(train, option=option)

            if reservation:
                logger.info(f"Successfully reserved train: {reservation}")
            return reservation

        except SoldOutError:
            logger.debug(f"Train sold out during reservation attempt: {train}")
            return None
        except Exception as e:
            logger.error(f"Error reserving train: {e}")
            return None

    def search_and_reserve_loop(
        self,
        dep_date: str,
        src_locate: str,
        dst_locate: str,
        dep_time: str = "000000",
        max_dep_time: str = "2400",
        train_type: TrainType = TrainType.KTX,
        reserve_option: ReserveOption = ReserveOption.GENERAL_FIRST,
        max_attempts: Optional[int] = None
    ):
        """
        Continuously search for trains and attempt reservation until successful.

        Args:
            dep_date: Departure date (YYYYMMDD)
            src_locate: Source station
            dst_locate: Destination station
            dep_time: Departure time (HHMMSS)
            max_dep_time: Maximum departure time (HHMM)
            train_type: Train type filter
            reserve_option: Reservation option
            max_attempts: Maximum attempts (None for infinite)

        Returns:
            Reservation object when successful, None if max_attempts reached
        """
        if not self._logged_in:
            raise ValueError("Must login before searching")

        attempts = 0
        logger.info(
            f"Starting reservation loop: {src_locate} -> {dst_locate} "
            f"on {dep_date} at {dep_time}"
        )

        while True:
            attempts += 1
            if max_attempts and attempts > max_attempts:
                logger.warning(f"Reached max attempts ({max_attempts}), stopping")
                return None

            # Search for trains
            trains = self.search_trains(
                dep_date, src_locate, dst_locate, dep_time, max_dep_time, train_type
            )

            # Try to reserve each train found
            for train in trains:
                logger.info(f"Found train: {train}, attempting reservation...")
                reservation = self.reserve_train(train, option=reserve_option)

                if reservation:
                    logger.info(f"Reservation successful after {attempts} attempts")
                    return reservation
                else:
                    logger.debug("Reservation failed, continuing search...")

            # Wait before next search
            time.sleep(self._search_interval)

    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._logged_in
