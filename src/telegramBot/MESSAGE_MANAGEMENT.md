# 메시지 관리 시스템

## 개요

텔레그램 봇의 모든 메시지를 중앙에서 관리하여 유지보수성을 향상시킨 시스템입니다.

## 구조

### 1. `messages.py` - 메시지 템플릿 모듈

모든 봇 메시지가 정의된 중앙 저장소입니다.

#### Messages 클래스

메시지 상수와 템플릿 메서드를 제공합니다.

**정적 메시지 (상수)**
```python
Messages.WELCOME          # 시작 메시지
Messages.HELP             # 도움말 메시지
Messages.LOGIN_SUCCESS    # 로그인 성공 메시지
Messages.ERROR_GENERIC    # 일반 에러 메시지
# ... 등등
```

**동적 메시지 (메서드)**
```python
Messages.status_info(count, users)               # 예약 상태 정보
Messages.subscriber_started(username, src, dst, date)  # 예약 시작 알림
Messages.CONFIRM_RESERVATION.format(...)         # 예약 정보 확인
```

#### MessageService 클래스

메시지 전송을 담당하는 서비스 클래스입니다.

**메서드:**
- `send(chat_id, message)` - 단일 사용자에게 메시지 전송
- `send_to_multiple(chat_ids, message)` - 여러 사용자에게 메시지 전송

**사용 예시:**
```python
# 초기화
msg_service = MessageService(session, send_url)

# 단일 전송
msg_service.send(chat_id, Messages.WELCOME)

# 포맷팅된 메시지 전송
msg_service.send(chat_id, Messages.status_info(5, ["user1", "user2"]))

# 다중 전송
msg_service.send_to_multiple(subscribers, Messages.SUBSCRIBE_SUCCESS)
```

## 주요 개선사항

### 1. **코드와 메시지 분리**
- 비즈니스 로직과 메시지 내용이 명확히 분리됨
- 메시지 수정 시 로직 코드를 건드리지 않아도 됨

### 2. **유지보수성 향상**
- 모든 메시지가 한 곳에 정리되어 관리가 용이
- 메시지 변경 시 `messages.py`만 수정하면 됨
- 중복 메시지 제거

### 3. **일관성 확보**
- 메시지 형식이 통일됨
- 재사용 가능한 메시지 템플릿

### 4. **확장성**
- 다국어 지원 추가가 용이 (향후 확장 가능)
- 메시지 A/B 테스트 가능
- 환경별 메시지 변경 용이 (개발/운영)

### 5. **코드 가독성**
- Before: 함수 내부에 긴 문자열이 있어 로직 파악 어려움
- After: `Messages.WELCOME`처럼 명확한 상수명으로 의도 파악 쉬움

## 메시지 카테고리

### 시작 및 안내
- `INIT`, `WELCOME`, `HELP`

### 로그인 관련
- `REQUEST_PHONE`, `REQUEST_PASSWORD`
- `LOGIN_SUCCESS`, `LOGIN_FAILED_RETRY`

### 예약 정보 입력
- `REQUEST_DATE`, `REQUEST_SRC_STATION`, `REQUEST_DST_STATION`
- `REQUEST_DEP_TIME`, `REQUEST_TRAIN_TYPE`, `REQUEST_SEAT_TYPE`
- `CONFIRM_RESERVATION`, `RESERVATION_STARTED`, `ALREADY_RUNNING`

### 에러 메시지
- `ERROR_GENERIC`, `ERROR_INVALID_COMMAND`, `ERROR_NO_PROGRESS`
- `ERROR_PHONE_FORMAT`, `ERROR_DATE_FORMAT`, `ERROR_TIME_FORMAT`
- `ERROR_TRAIN_TYPE_INVALID`, `ERROR_SEAT_TYPE_INVALID`

### 취소 및 완료
- `CANCELLED`, `CANCELLED_BY_USER`, `PAYMENT_CONFIRMED`

### 구독 관련
- `SUBSCRIBE_SUCCESS`, `SUBSCRIBE_ALREADY`

### 관리자
- `ADMIN_FORCE_CANCEL`, `ADMIN_BROADCAST_DEFAULT`

## 향후 확장 가능성

### 1. 다국어 지원
```python
class Messages:
    @staticmethod
    def get_message(key, lang='ko'):
        messages = {
            'ko': {'WELCOME': '근삼 코레일 봇...'},
            'en': {'WELCOME': 'Welcome to Korail Bot...'}
        }
        return messages[lang][key]
```

### 2. 외부 설정 파일
```python
# config/messages.yaml
welcome:
  ko: "근삼 코레일 봇..."
  en: "Welcome to Korail Bot..."
```

### 3. 동적 메시지 로딩
```python
class Messages:
    def __init__(self):
        self.messages = self.load_from_db()
```

## 마이그레이션 가이드

기존 코드:
```python
msg = "예약이 취소되었습니다."
self.sendMessage(chatId, msg)
```

새 코드:
```python
self.msg_service.send(chatId, Messages.CANCELLED)
```

동적 메시지 (포맷팅):
```python
# 기존
msg = f"총 {count}개의 예약이 실행중입니다."

# 새로운 방식
msg = Messages.status_info(count, users)
```

## 장점 요약

1. ✅ **중앙 집중 관리**: 모든 메시지를 한 곳에서 관리
2. ✅ **코드 간결화**: 400줄 이상의 메시지 문자열을 제거
3. ✅ **타입 안정성**: 상수로 정의되어 오타 방지
4. ✅ **재사용성**: 같은 메시지를 여러 곳에서 사용 가능
5. ✅ **테스트 용이성**: 메시지와 로직을 독립적으로 테스트 가능
