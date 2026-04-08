"""Station name validation and management for Korail."""
import json
import requests
from typing import Set, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# API endpoint for station data
KORAIL_STATION_DB_URL = "https://smart.letskorail.com:443/classes/com.korail.mobile.common.stationdata"

# Redis cache key and TTL
REDIS_STATION_CACHE_KEY = "korail:station_list"
REDIS_STATION_CACHE_TTL = 86400  # 24 hours

# Fallback static list in case API and Redis fail
FALLBACK_STATIONS = {
    # 수도권
    "서울", "용산", "영등포", "광명", "수원", "천안아산", "행신", "청량리",
    "왕십리", "수색", "의정부", "동두천", "소요산", "평택", "성환", "아산",

    # 강원권
    "강릉", "동해", "정동진", "평창", "진부", "횡성", "원주", "제천", "태백",
    "영주", "안동", "묵호", "삼척", "춘천", "남춘천",

    # 충청권
    "대전", "서대전", "세종", "천안", "조치원", "청주", "오송", "충주",
    "단양", "영동", "김천", "옥천",

    # 전라권
    "전주", "익산", "정읍", "광주", "광주송정", "목포", "여수엑스포", "순천",
    "나주", "송정리", "광주송정", "구례구", "남원", "곡성", "임실", "김제",

    # 경상권
    "대구", "동대구", "서대구", "김천구미", "구미", "포항", "경주", "울산",
    "부산", "마산", "창원", "진주", "밀양", "김해", "구포", "부전", "거제",
    "진영", "통도사", "신경주", "경산", "삼랑진", "창원중앙",

    # 호남선
    "논산", "강경", "함열", "신태인",

    # 경전선
    "하동", "광양", "율촌", "진상", "덕산", "함안",

    # 동해선
    "일광", "기장", "태화강", "남창", "덕하",

    # 중앙선
    "청량리역", "상봉", "양평", "용문", "지평", "도담", "풍기",

    # 기타
    "신탄리", "지제", "매포", "증평", "음성", "주덕", "충주", "가은",
}


class StationManager:
    """Manages station data with Redis caching."""

    _instance: Optional['StationManager'] = None
    _redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StationManager, cls).__new__(cls)
            cls._instance._initialize_redis()
        return cls._instance

    def _initialize_redis(self):
        """Initialize Redis client (lazy loading)."""
        try:
            from config.settings import settings
            import redis

            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self._redis_client.ping()
            logger.info("StationManager: Redis connected for station caching")
        except Exception as e:
            logger.warning(f"StationManager: Redis connection failed: {e}")
            logger.warning("StationManager: Will operate without Redis caching")
            self._redis_client = None

    def _fetch_stations_from_api(self) -> Set[str]:
        """
        Fetch station list from Korail API.

        Returns:
            Set of station names
        """
        try:
            logger.info("Fetching station data from Korail API...")
            response = requests.get(
                KORAIL_STATION_DB_URL,
                headers={
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 5.1.1; Nexus 4 Build/LMY48T)'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # API 응답 구조에 따라 파싱
                if isinstance(data, dict) and 'stationList' in data:
                    stations = {station['stationName'] for station in data['stationList']}
                    logger.info(f"Successfully fetched {len(stations)} stations from API")
                    return stations
                elif isinstance(data, list):
                    stations = {station.get('name', '') for station in data if station.get('name')}
                    logger.info(f"Successfully fetched {len(stations)} stations from API")
                    return stations
                else:
                    logger.warning(f"Unexpected API response format: {type(data)}")
                    return FALLBACK_STATIONS

            logger.warning(f"API returned status code {response.status_code}")
            return FALLBACK_STATIONS

        except requests.exceptions.Timeout:
            logger.warning("API request timed out, using fallback station list")
            return FALLBACK_STATIONS
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch stations from API: {e}")
            return FALLBACK_STATIONS
        except Exception as e:
            logger.error(f"Unexpected error fetching station data: {e}", exc_info=True)
            return FALLBACK_STATIONS

    def _get_from_redis(self) -> Optional[Set[str]]:
        """
        Get station list from Redis cache.

        Returns:
            Set of station names or None if cache miss
        """
        if not self._redis_client:
            return None

        try:
            cached_data = self._redis_client.get(REDIS_STATION_CACHE_KEY)
            if cached_data:
                stations = set(json.loads(cached_data))
                logger.info(f"Loaded {len(stations)} stations from Redis cache")
                return stations
        except Exception as e:
            logger.warning(f"Failed to load stations from Redis: {e}")

        return None

    def _save_to_redis(self, stations: Set[str]) -> None:
        """
        Save station list to Redis cache.

        Args:
            stations: Set of station names
        """
        if not self._redis_client:
            return

        try:
            data = json.dumps(list(stations))
            self._redis_client.setex(
                REDIS_STATION_CACHE_KEY,
                REDIS_STATION_CACHE_TTL,
                data
            )
            logger.info(f"Saved {len(stations)} stations to Redis cache (TTL={REDIS_STATION_CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"Failed to save stations to Redis: {e}")

    def get_valid_stations(self, force_refresh: bool = False) -> Set[str]:
        """
        Get valid station names with multi-tier caching.

        Caching strategy:
        1. Try Redis cache (24h TTL)
        2. If cache miss, fetch from API
        3. If API fails, use fallback static list
        4. Save successful API result to Redis

        Args:
            force_refresh: Force refresh from API

        Returns:
            Set of valid station names
        """
        # Try Redis cache first (unless forced refresh)
        if not force_refresh:
            cached_stations = self._get_from_redis()
            if cached_stations:
                return cached_stations

        # Fetch from API
        logger.info("Fetching fresh station data...")
        stations = self._fetch_stations_from_api()

        # Save to Redis if not fallback
        if stations != FALLBACK_STATIONS:
            self._save_to_redis(stations)

        return stations


# Global station manager instance
_station_manager = StationManager()


def get_valid_stations(force_refresh: bool = False) -> Set[str]:
    """
    Get the current set of valid station names.

    Args:
        force_refresh: Force refresh from API

    Returns:
        Set of valid station names
    """
    return _station_manager.get_valid_stations(force_refresh=force_refresh)


def is_valid_station(station_name: str) -> bool:
    """
    Check if station name is valid.

    Args:
        station_name: Station name (without '역')

    Returns:
        True if station is valid, False otherwise
    """
    if not station_name:
        return False

    # Get valid stations from cache/API
    valid_stations = get_valid_stations()

    # 정확히 일치하는 역명 확인
    return station_name in valid_stations


def get_similar_stations(station_name: str, max_results: int = 5) -> list:
    """
    Get similar station names for suggestion.

    Args:
        station_name: User input station name
        max_results: Maximum number of suggestions

    Returns:
        List of similar station names
    """
    if not station_name:
        return []

    # Get valid stations from cache/API
    valid_stations = get_valid_stations()

    # 정확히 일치하면 빈 리스트 반환
    if station_name in valid_stations:
        return []

    matches = []

    # 1. 부분 문자열 매칭 (포함 관계)
    for valid_station in valid_stations:
        if station_name in valid_station or valid_station in station_name:
            matches.append(valid_station)

    # 2. 첫 글자 매칭 (접두사)
    if not matches and len(station_name) >= 1:
        for valid_station in valid_stations:
            if valid_station.startswith(station_name[0]):
                matches.append(valid_station)

    # 중복 제거 및 정렬
    matches = sorted(list(set(matches)))

    return matches[:max_results]


def format_station_suggestions(similar_stations: list) -> str:
    """
    Format station suggestions for display.

    Args:
        similar_stations: List of similar station names

    Returns:
        Formatted suggestion string
    """
    if not similar_stations:
        return ""

    if len(similar_stations) == 1:
        return f"\n\n혹시 '{similar_stations[0]}'을(를) 찾으시나요?"

    suggestions = ", ".join(similar_stations)
    return f"\n\n비슷한 역: {suggestions}"
