# 리팩터링 가이드

## 개요

이 문서는 Korail KTX 예매 텔레그램 챗봇의 대규모 리팩터링 내용을 설명합니다.

## 목표

1. **관심사의 분리**: 비즈니스 로직, API 핸들링, 상태 관리 분리
2. **유지보수성 향상**: 모듈화를 통한 코드 가독성 및 테스트 용이성 개선
3. **확장성**: 새 기능 추가 시 기존 코드 영향 최소화
4. **타입 안전성**: Python 타입 힌트 추가

## 변경 전/후 비교

### 기존 구조 (Before)
```
src/
├── app.py (15 lines)
└── telegramBot/
    ├── telebotApiHandler.py (693 lines) ⚠️ 너무 비대
    ├── korailReserve.py (200 lines)
    └── telebotBackProcess.py (34 lines)
```

**문제점:**
- `telebotApiHandler.py`가 693줄로 너무 큼
- 모든 로직이 한 클래스에 집중 (단일 책임 원칙 위반)
- 전역 상태 관리 (클래스 변수)
- 하드코딩된 설정 값
- 타입 힌트 없음
- 테스트 어려움

### 새로운 구조 (After)
```
src/
├── app.py                          # Flask 앱 진입점
├── config/
│   └── settings.py                 # 중앙화된 설정 관리
├── models/
│   ├── user.py                     # 사용자 데이터 모델
│   └── reservation.py              # 예약 데이터 모델
├── services/                       # 비즈니스 로직
│   ├── korail_service.py           # Korail API 래퍼
│   ├── telegram_service.py         # Telegram 메시징
│   ├── reservation_service.py      # 예약 오케스트레이션
│   └── payment_reminder_service.py # 결제 리마인더
├── storage/                        # 상태 관리 추상화
│   ├── base.py                     # Storage 인터페이스
│   └── memory.py                   # In-memory 구현
├── api/                            # API 엔드포인트
│   ├── telegram_webhook.py
│   └── payment_check.py
├── handlers/                       # 요청 핸들러
│   ├── command_handler.py
│   └── conversation_handler.py
└── utils/
    └── logger.py                   # 구조화된 로깅
```

## 주요 개선 사항

### 1. 설정 관리 (config/settings.py)

**Before:**
```python
BOTTOKEN = os.environ.get('BOTTOKEN')
interval = 1  # 하드코딩
```

**After:**
```python
from config.settings import settings

settings.TELEGRAM_BOT_TOKEN
settings.KORAIL_SEARCH_INTERVAL
settings.PAYMENT_TIMEOUT_MINUTES
```

### 2. 데이터 모델 (models/)

**Before:** 딕셔너리로 데이터 관리
```python
userDict = {
    123123: {
        "inProgress": True,
        "lastAction": 2,
        ...
    }
}
```

**After:** 타입 안전한 데이터클래스
```python
from models import UserSession, TrainSearchParams

session = UserSession(
    chat_id=123123,
    in_progress=True,
    last_action=2
)
```

### 3. 서비스 레이어 분리

**Before:** 모든 로직이 `Index` 클래스에
```python
class Index(Resource):
    def sendMessage(self, chatId, text):
        # Telegram API 호출

    def login(self, username, password):
        # Korail 로그인

    def reserve(self, ...):
        # 예약 로직

    # ... 50+ 메서드
```

**After:** 책임별로 분리
```python
# services/telegram_service.py
class TelegramService:
    def send_message(self, chat_id, text): ...

# services/korail_service.py
class KorailService:
    def login(self, username, password): ...
    def search_trains(self, ...): ...

# services/reservation_service.py
class ReservationService:
    def start_reservation_process(self, ...): ...
```

### 4. Storage 추상화

**Before:** 클래스 변수로 상태 관리
```python
class Index(Resource):
    userDict = {}  # 전역 상태
    runningStatus = {}
    paymentCompleted = {}
```

**After:** Storage 인터페이스
```python
# storage/base.py
class StorageInterface(ABC):
    @abstractmethod
    def get_user_session(self, chat_id): ...
    @abstractmethod
    def save_user_session(self, session): ...

# storage/memory.py
class InMemoryStorage(StorageInterface):
    # 현재 동작과 동일하지만 추상화됨
    # 향후 Redis 등으로 쉽게 교체 가능
```

### 5. 로깅

**Before:**
```python
print(f'열차 발견 : {train}')
```

**After:**
```python
from utils.logger import get_logger
logger = get_logger(__name__)

logger.info(f"Found train: {train}")
logger.error(f"Reservation failed: {e}")
```

### 6. 메시지 템플릿

**Before:** 메시지가 코드 곳곳에 하드코딩
```python
msg = """
근삼 코레일 봇을 이용해 주셔사 감사합니다.
본 프로그램은 ...
"""
self.sendMessage(chatId, msg)
```

**After:** 중앙화된 템플릿
```python
from services.telegram_service import MessageTemplates

message = MessageTemplates.welcome_message()
telegram_service.send_message(chat_id, message)
```

## 마이그레이션 전략

### Phase 1: 기반 구조 ✅
- [x] 폴더 구조 생성
- [x] 설정 관리 시스템 (config/)
- [x] 로깅 시스템 (utils/logger.py)
- [x] 데이터 모델 (models/)
- [x] Storage 인터페이스 (storage/)

### Phase 2: 서비스 레이어 ✅
- [x] TelegramService 추출
- [x] KorailService 추출
- [x] ReservationService 추출
- [x] PaymentReminderService 추출

### Phase 3: API 핸들러 (진행 중)
- [ ] 기존 코드 백업
- [ ] 새 구조와 호환되는 브리지 레이어 작성
- [ ] 점진적 마이그레이션
- [ ] 통합 테스트

### Phase 4: 테스트 강화
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 커버리지 80% 이상

### Phase 5: 문서화 및 배포
- [ ] 코드 문서화
- [ ] README 업데이트
- [ ] 배포

## 하위 호환성

기존 코드가 계속 작동하도록 하기 위해:
1. `telegramBot/` 디렉토리는 당분간 유지
2. 새 서비스는 의존성 주입으로 구현하여 독립적으로 테스트 가능
3. 점진적 마이그레이션: 한 번에 하나의 기능씩 이전

## 테스트 방법

### 기존 테스트 실행
```bash
make test
```

### 새 서비스 단위 테스트 (작성 예정)
```bash
pytest tests/unit/
```

## 롤백 계획

문제 발생 시:
1. `telegramBot/` 디렉토리의 기존 코드로 복귀
2. `app.py`에서 기존 import 복원
3. 새 디렉토리는 삭제하지 않고 유지 (향후 재시도)

## 다음 단계

1. 기존 `telebotApiHandler.py` 분석
2. 새 서비스 레이어를 사용하는 브리지 작성
3. 점진적으로 기능 이전
4. 각 단계마다 테스트

## 기여자 노트

- 새 코드 작성 시 타입 힌트 필수
- 로깅은 `utils.logger` 사용 (print 금지)
- 설정값은 `config.settings`에서 가져오기
- 새 기능은 적절한 서비스에 추가
