# 대화 플로우 문서

이 문서는 텔레그램 봇의 예약 프로세스 전체 대화 플로우를 정리합니다.

## 전체 플로우 개요

| 단계 | Progress 상태 | 핸들러 메서드 | 사용자 입력 | 응답 메시지 | 다음 상태 |
|-----|--------------|-------------|-----------|-----------|---------|
| 0 | INIT | - | - | - | - |
| 1 | STARTED | `_handle_start_confirmation` | "Y" 또는 "예" | REQUEST_PHONE (전화번호 요청) | START_ACCEPTED |
| 1-1 | STARTED | `_handle_admin_login` | "근삼이최고" | LOGIN_SUCCESS (환경변수 자동로그인) | PW_INPUT_SUCCESS |
| 2 | START_ACCEPTED | `_handle_phone_input` | 010-1234-5678 | REQUEST_PASSWORD (비밀번호 요청) | ID_INPUT_SUCCESS |
| 3 | ID_INPUT_SUCCESS | `_handle_password_input` | 비밀번호 | LOGIN_SUCCESS (로그인 성공) | PW_INPUT_SUCCESS |
| 4 | PW_INPUT_SUCCESS | `_handle_date_input` | 20260408 | REQUEST_DATE (✅ 출발일 입력 완료 + 출발역 요청) | DATE_INPUT_SUCCESS |
| 5 | DATE_INPUT_SUCCESS | `_handle_src_station_input` | 광주송정 | REQUEST_SRC_STATION (✅ 출발역 입력 완료 + 도착역 요청) | SRC_LOCATE_INPUT_SUCCESS |
| 6 | SRC_LOCATE_INPUT_SUCCESS | `_handle_dst_station_input` | 대전 | "도착역 입력 완료" + 시간 입력 요청 | DST_LOCATE_INPUT_SUCCESS |
| 7 | DST_LOCATE_INPUT_SUCCESS | `_handle_dep_time_input` | 1200 | "검색 시작 시각 완료" + 최대 시각 요청 | DEP_TIME_INPUT_SUCCESS |
| 8 | DEP_TIME_INPUT_SUCCESS | `_handle_max_dep_time_input` | 2400 | "기준 시각 완료" + 열차 타입 선택 | MAX_DEP_TIME_INPUT_SUCCESS |
| 9 | MAX_DEP_TIME_INPUT_SUCCESS | `_handle_train_type_input` | 1 또는 2 | "열차 타입 완료" + 특실 옵션 선택 | TRAIN_TYPE_INPUT_SUCCESS |
| 10 | TRAIN_TYPE_INPUT_SUCCESS | `_handle_special_option_input` | 1~4 | "특실 타입 완료" + 탑승 인원 요청 | SPECIAL_INPUT_SUCCESS |
| 11 | SPECIAL_INPUT_SUCCESS | `_handle_passenger_count_input` | 1~9 | 인원수별 좌석 배치 선택 요청 | PASSENGER_COUNT_INPUT_SUCCESS |
| 12 | PASSENGER_COUNT_INPUT_SUCCESS | `_handle_seat_strategy_input` | 1 또는 2 | 최종 확인 화면 | SEAT_STRATEGY_INPUT_SUCCESS |
| 13 | SEAT_STRATEGY_INPUT_SUCCESS | `_handle_final_confirmation` | "Y" 또는 "예" | "예약 시작" | FINDING_TICKET |

## 상세 플로우

### 1단계: 시작 확인 (STARTED)
**입력**:
- "Y" 또는 "예" → 정상 진행
- "근삼이최고" → 관리자 자동 로그인 (환경변수 USERID, USERPW 사용)

**응답**:
- 정상: REQUEST_PHONE (전화번호 입력 요청)
- 관리자: LOGIN_SUCCESS (자동 로그인 후 날짜 입력 단계로)

---

### 2단계: 전화번호 입력 (START_ACCEPTED)
**입력**: `010-1234-5678` (하이픈 포함 필수)

**검증**:
- 하이픈 포함 여부
- 전화번호 형식 (010-xxxx-xxxx)
- ALLOW_LIST 확인 (허용된 사용자인지)

**응답**: REQUEST_PASSWORD (비밀번호 입력 요청)

---

### 3단계: 비밀번호 입력 (ID_INPUT_SUCCESS)
**입력**: 코레일 비밀번호

**검증**:
- 코레일 API 로그인 시도
- 실패 시: 재입력 요청 (상태 유지)

**응답**: LOGIN_SUCCESS (로그인 성공 + 출발일 입력 요청)

---

### 4단계: 출발일 입력 (PW_INPUT_SUCCESS)
**입력**: `20260408` (8자리 숫자)

**검증**:
- 8자리 숫자
- 유효한 날짜
- 과거 날짜 아닌지

**응답**:
- Messages.REQUEST_DATE
- "✅ 출발일 입력 완료" + 출발역 입력 요청
- 역 목록 URL 제공

---

### 5단계: 출발역 입력 (DATE_INPUT_SUCCESS)
**입력**: `광주송정` (역 이름, "역" 제외)

**검증**:
- "역" 포함 여부 (포함하면 에러)
- 최소 2글자 이상

**응답**:
- Messages.REQUEST_SRC_STATION
- "✅ 출발역 입력 완료" + 도착역 입력 요청

---

### 6단계: 도착역 입력 (SRC_LOCATE_INPUT_SUCCESS)
**입력**: `대전` (역 이름, "역" 제외)

**검증**: 출발역과 동일

**응답**:
- 인라인 메시지
- "✅ 도착역 입력 완료" + 검색 시작 시각 입력 요청
- 형식: HHMM (예: 1305)

---

### 7단계: 검색 시작 시각 입력 (DST_LOCATE_INPUT_SUCCESS)
**입력**: `1200` (4자리 시간, 0-23시 기준)

**검증**:
- 4자리 숫자
- 시간: 0-23
- 분: 0-59

**응답**:
- "검색 시작 시각 완료" + 최대 시각 입력 요청
- 2400 입력 가능 (제한 없음)

---

### 8단계: 검색 최대 시각 입력 (DEP_TIME_INPUT_SUCCESS)
**입력**: `2400` 또는 4자리 시간

**특수 처리**: `2400`은 제한 없음을 의미 (권장)

**응답**:
- "기준 시각 완료" + 열차 타입 선택 요청
- 1: KTX만
- 2: 모든 열차

---

### 9단계: 열차 타입 선택 (MAX_DEP_TIME_INPUT_SUCCESS)
**입력**: `1` 또는 `2`

**저장**:
- 1 → trainType: "TrainType.KTX", trainTypeShow: "KTX"
- 2 → trainType: "TrainType.ALL", trainTypeShow: "ALL"

**응답**:
- "열차 타입 완료" + 특실 옵션 선택 요청
- 1: 일반실 우선
- 2: 일반실만
- 3: 특실 우선
- 4: 특실만

---

### 10단계: 특실 옵션 선택 (TRAIN_TYPE_INPUT_SUCCESS)
**입력**: `1`, `2`, `3`, 또는 `4`

**저장**:
- 1 → ReserveOption.GENERAL_FIRST
- 2 → ReserveOption.GENERAL_ONLY
- 3 → ReserveOption.SPECIAL_FIRST
- 4 → ReserveOption.SPECIAL_ONLY

**응답**:
- "특실 타입 완료" + 탑승 인원수 입력 요청
- 1~9명 입력 가능

---

### 11단계: 탑승 인원수 입력 (SPECIAL_INPUT_SUCCESS)
**입력**: `1`~`9`

**검증**:
- 숫자인지
- 1~9 범위인지

**응답**:
- 1명: 자동으로 좌석 배치 'consecutive' 설정 후 최종 확인으로
- 2명 이상: 좌석 배치 방식 선택 요청
  - 1: 연속 좌석 (권장)
  - 2: 랜덤 배치

---

### 12단계: 좌석 배치 방식 선택 (PASSENGER_COUNT_INPUT_SUCCESS)
**입력**: `1` 또는 `2` (2명 이상일 때만)

**저장**:
- 1 → seatStrategy: "consecutive", seatStrategyShow: "연속 좌석"
- 2 → seatStrategy: "random", seatStrategyShow: "랜덤 배치"

**응답**: 최종 확인 화면

---

### 13단계: 최종 확인 (SEAT_STRATEGY_INPUT_SUCCESS)
**화면**: 입력한 모든 정보 요약
- 출발일
- 출발역
- 도착역
- 검색시작시각
- 검색최대시각
- 열차타입
- 특실여부
- 탑승인원
- 좌석배치

**입력**:
- "Y" 또는 "예" → 예약 시작
- "N" 또는 "아니오" → 작업 취소

**응답**: RESERVATION_STARTED (예약 프로세스 시작)

---

## 특수 케이스

### 로그인 실패 처리
- 비밀번호 입력 실패 시 상태를 유지하고 재입력 요청
- 사용자가 "Y" 입력 시 처음부터 다시 시작
- 사용자가 "N" 입력 시 취소
- 그 외 입력: 비밀번호 재시도

### 매직 로그인 ("근삼이최고")
- 환경변수 USERID, USERPW 사용
- 자동 로그인 후 PW_INPUT_SUCCESS 상태로 진입
- 로그인 실패 시 세션 초기화

### 1명 예약 시
- 좌석 배치 선택 단계 자동 건너뛰기
- 자동으로 'consecutive' 설정

---

## 로직 헷갈림 포인트 분석

### 🔴 문제점 1: 메서드명과 실제 동작 불일치

**현재 상황**:
```python
def request_departure_station():
    """Request departure station after date input"""
    return Messages.REQUEST_DATE  # "출발일 입력 완료" 메시지
```

**헷갈리는 이유**:
- 메서드명: `request_departure_station` (출발역을 요청한다)
- 실제 동작: `REQUEST_DATE` 반환 (출발일 입력 완료 메시지)
- **메서드명이 "무엇을 요청하는지"가 아니라 "언제 호출되는지"를 나타내야 함**

**개선 제안**:
```python
# 옵션 1: 메서드명을 반환 메시지에 맞추기
def confirm_date_request_departure_station():
    return Messages.REQUEST_DATE

# 옵션 2: 상수명을 단계별로 명확히 하기
REQUEST_AFTER_DATE_INPUT = "출발일 입력 완료 + 출발역 요청"
REQUEST_AFTER_SRC_STATION_INPUT = "출발역 입력 완료 + 도착역 요청"
```

### 🔴 문제점 2: Progress 상태명이 "입력 성공"으로 끝남

**현재 상황**:
```python
UserProgress.DATE_INPUT_SUCCESS  # 날짜 입력 성공
# → 다음 단계에서 출발역 입력을 받음
```

**헷갈리는 이유**:
- 상태명: `DATE_INPUT_SUCCESS` (날짜 입력 성공)
- 실제 의미: "날짜 입력이 완료되어 **출발역을 기다리는 중**"
- 상태명만 보면 "다음에 무엇을 받아야 하는지" 불명확

**개선 제안**:
```python
# 옵션 1: "WAITING_FOR" 패턴
UserProgress.WAITING_FOR_SRC_STATION
UserProgress.WAITING_FOR_DST_STATION

# 옵션 2: "NEED" 패턴
UserProgress.NEED_SRC_STATION_INPUT
UserProgress.NEED_DST_STATION_INPUT
```

### 🔴 문제점 3: 메시지 상수가 "확인 + 요청"을 동시에 포함

**현재 상황**:
```python
REQUEST_DATE = """✅ 출발일 입력 완료

🚉 출발역을 입력해주세요.
"""
```

**헷갈리는 이유**:
- 하나의 메시지가 "완료 확인"과 "다음 요청"을 동시에 함
- 메시지 이름 `REQUEST_DATE`는 날짜를 요청하는 것 같지만, 실제로는 날짜 완료 확인 + 출발역 요청

**개선 제안**:
```python
# 명확한 이름
CONFIRM_DATE_AND_REQUEST_SRC = "출발일 입력 완료 + 출발역 요청"
CONFIRM_SRC_AND_REQUEST_DST = "출발역 입력 완료 + 도착역 요청"
```

---

## 개선 제안 요약

### ✅ 현재 작동하는 매핑 (수정 완료)
```python
# conversation_handler.py
_handle_date_input → request_departure_station() → REQUEST_DATE
_handle_src_station_input → request_arrival_station() → REQUEST_SRC_STATION
```

### 🎯 근본적인 리팩토링 방향

1. **메시지 상수명을 단계별로 명확하게**
   ```python
   AFTER_DATE_INPUT = "✅ 출발일 입력 완료 + 출발역 요청"
   AFTER_SRC_INPUT = "✅ 출발역 입력 완료 + 도착역 요청"
   AFTER_DST_INPUT = "✅ 도착역 입력 완료 + 시간 요청"
   ```

2. **Progress 상태를 "다음 입력 대기" 패턴으로**
   ```python
   AWAITING_PHONE_INPUT
   AWAITING_PASSWORD_INPUT
   AWAITING_DATE_INPUT
   AWAITING_SRC_STATION_INPUT
   ```

3. **메서드명을 "확인 + 요청" 패턴으로**
   ```python
   def confirm_date_and_request_src_station()
   def confirm_src_and_request_dst_station()
   ```

---

## 결론

**현재 상태**: ✅ 기능은 정상 작동 (메시지 매핑 수정 완료)

**헷갈리는 이유**:
1. 메서드명이 실제 반환 메시지와 불일치
2. Progress 상태명이 "완료"를 나타내지만 실제로는 "대기 중"
3. 메시지 상수가 "확인 + 요청"을 동시에 포함

**리팩토링 필요성**:
- 긴급하지 않음 (기능 정상 작동)
- 코드 가독성과 유지보수성 향상을 위해 추후 개선 권장
- 기존 코드를 건드릴 때 breaking change 발생 가능성 있음
