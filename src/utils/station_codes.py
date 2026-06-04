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

# Fallback static list (snapshot from Korail API on 2026-06-02).
# Used only when both Redis cache and API request fail.
FALLBACK_STATIONS = {
    "가남", "가평", "각계", "감곡장호원", "강경", "강구", "강릉", "강진",
    "강촌", "개포", "경산", "경주", "계룡", "고래불", "고한", "곡성",
    "공주", "광명", "광양", "광주", "광주송정", "광천", "구례구", "구미",
    "구포", "군북", "군산", "군위", "극락강", "근덕", "기성", "기장",
    "김제", "김천", "김천구미", "나전", "나주", "남성현", "남원", "남창",
    "남춘천", "논산", "능주", "다시", "단양", "대곡", "대구", "대야",
    "대전", "대천", "덕소", "도계", "도고온천", "도라산", "동대구", "동백산",
    "동탄", "동해", "둔내", "득량", "마산", "마석", "만종", "매곡",
    "매화", "명봉", "목포", "몽탄", "무안", "묵호", "문경", "문산",
    "물금", "민둥산", "밀양", "반성", "백양리", "백양사", "벌교", "별어곡",
    "보성", "봉양", "봉화", "부강", "부발", "부산", "부전", "북영천",
    "북울산", "북천", "분천", "비동", "사릉", "사북", "사상", "살미",
    "삼랑진", "삼례", "삼산", "삼척", "삼척해변", "삼탄", "삽교", "상동",
    "상봉", "상주", "서경주", "서광주", "서대구", "서대전", "서울", "서원주",
    "서정리", "서천", "서화성", "석불", "석포", "선평", "성환", "센텀",
    "송추", "수서", "수안보온천", "수원", "순천", "승부", "신기", "신동",
    "신례원", "신보성", "신창", "신탄진", "신태인", "신해운대", "심천", "쌍룡",
    "아산", "아우라지", "아화", "안강", "안동", "안양", "안중", "앙성온천",
    "약목", "양동", "양원", "양평", "여수EXPO", "여천", "연산", "연풍",
    "영덕", "영동", "영등포", "영암", "영월", "영주", "영천", "영해",
    "예당", "예미", "예산", "예천", "오근장", "오산", "오송", "오수",
    "옥산", "옥수", "옥원", "옥천", "온양온천", "완사", "왕십리", "왜관",
    "용궁", "용문", "용산", "운천", "울산(통도사)", "울진", "웅천", "원동",
    "원릉", "원주", "월포", "음성", "의성", "의정부", "이양", "이원",
    "익산", "인주", "인천공항T1", "인천공항T2", "일로", "일신", "일영", "임기",
    "임성리", "임실", "임원", "임진강", "장동", "장사", "장성", "장항",
    "장흥", "전남장흥", "전의", "전주", "점촌", "정동진", "정선", "정읍",
    "제천", "조성", "조치원", "주덕", "죽변", "중리", "증평", "지탄",
    "지평", "진례", "진부(오대산)", "진상", "진영", "진주", "창원", "창원중앙",
    "천안", "천안아산", "철암", "청도", "청량리", "청리", "청소", "청주",
    "청주공항", "청평", "추암", "추풍령", "춘양", "춘천", "충주", "태백",
    "태화강", "퇴계원", "판교(경기)", "판교(충남)", "평내호평", "평창", "평택", "평택지제",
    "평해", "포항", "풍기", "하동", "하양", "한림정", "함안", "함열",
    "함창", "함평", "합덕", "해남", "행신", "향남", "현동", "홍성",
    "화명", "화성시청", "화순", "황간", "횡성", "횡천", "효천", "후포",
    "흥부",
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
                # 실측 응답 구조: {"stns": {"stn": [{"stn_nm": ..., ...}, ...]}}
                if isinstance(data, dict) and isinstance(data.get('stns'), dict):
                    stn_list = data['stns'].get('stn', [])
                    stations = {s['stn_nm'] for s in stn_list if s.get('stn_nm')}
                    if stations:
                        logger.info(f"Successfully fetched {len(stations)} stations from API")
                        return stations
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
