"""
텔레그램 봇 메시지 템플릿 관리

모든 봇 메시지를 중앙에서 관리하여 유지보수성을 향상시킵니다.
"""


class Messages:
    """봇 메시지 템플릿 클래스"""

    # ========== 시작 및 안내 메시지 ==========
    WELCOME = """🚄 근삼 코레일 봇을 이용해 주셔서 감사합니다.

본 프로그램은 매진 열차 자동 예약을 위한 서비스입니다.
예약 완료 시 결제는 10분 이내에 직접 진행해주셔야 합니다.

📋 예약 정보 입력 순서
━━━━━━━━━━━━━━━━
  1. 코레일 로그인 정보
  2. 출발 희망일
  3. 출발역
  4. 도착역
━━━━━━━━━━━━━━━━

계속 진행하시려면 "예" 또는 "Y"를 입력해주세요.
"""

    HELP = """📌 사용 가능한 명령어

🎫 예약 관련
  /start - 예약 시작
  /cancel - 진행 중인 예약 취소

ℹ️ 정보 확인
  /status - 예약 상태 확인
  /help - 도움말 보기

🔧 관리자 명령어 (인증 필요)
  /subscribe - 알림 구독
  /allusers - 전체 사용자 확인
  /cancelall - 전체 예약 취소
  /broadcast [메시지] - 공지사항 전송
  /flushredis - Redis 메모리 초기화 (⚠️ 위험)
  /debug_on - 상세 디버그 로그 활성화
  /debug_off - 디버그 로그 비활성화

💡 결제 알림은 예약 성공 후 아무 메시지나 입력하면 중단됩니다.
"""

    # ========== 로그인 관련 메시지 ==========
    REQUEST_PHONE = """📱 코레일 로그인 정보 입력을 시작합니다.

현재 휴대폰 번호 로그인만 지원됩니다.

휴대전화번호를 입력해 주세요.
예시: 010-1234-5678

⚠️ 하이픈(-)을 반드시 포함하여 입력해주세요.
💡 취소를 원하시면 /cancel을 입력하세요.
"""

    REQUEST_PASSWORD = """✅ 아이디 입력 완료

🔒 비밀번호를 입력해주세요.
"""

    LOGIN_SUCCESS = """✅ 로그인 성공!

📅 출발 희망일을 8자리로 입력해주세요.
예시: 20250425 (2025년 4월 25일)
"""

    LOGIN_FAILED_RETRY = """❌ 로그인 실패

입력하신 정보:
━━━━━━━━━━━━━━
아이디: {username}
비밀번호: 보안상 비공개
━━━━━━━━━━━━━━

다음 중 하나를 선택해주세요:
  • Y 또는 예 → 계정정보 다시 입력
  • N 또는 아니오 → 작업 취소
  • 비밀번호만 다시 입력 → 같은 아이디로 재시도

⚠️ 주의: 5회 이상 로그인 실패 시 코레일 홈페이지에서 비밀번호를 재설정해야 합니다.
"""

    # ========== 예약 정보 입력 메시지 ==========
    REQUEST_DATE = """✅ 출발일 입력 완료

🚉 출발역을 입력해주세요.
예시: 광명, 서울, 부산 등

💡 역 이름만 입력 ('역' 제외)
📍 역 목록: http://www.letskorail.com/ebizprd/stationKtxList.do
"""

    REQUEST_SRC_STATION = """✅ 출발역 입력 완료

🏁 도착역을 입력해주세요.
예시: 광주송정, 대전, 동대구 등

💡 역 이름만 입력 ('역' 제외)
📍 역 목록: http://www.letskorail.com/ebizprd/stationKtxList.do
"""

    REQUEST_DST_STATION = """✅ 도착역 입력 완료

🕐 검색 시작 시각을 입력해주세요.

형식: HHMM (24시간 기준, 4자리)
예시: 1305 (오후 1시 5분 이후 열차 검색)
"""

    REQUEST_DEP_TIME = """✅ 검색 시작 시각 입력 완료

🕐 검색 종료 시각을 입력해주세요.

형식: HHMM (24시간 기준, 4자리)
예시: 1800 (오후 6시까지의 열차만 검색)

💡 시간 제한 없이 검색하려면 2400 입력 (권장)
"""

    REQUEST_TRAIN_TYPE = """✅ 시간 입력 완료

🚄 열차 종류를 선택해주세요.

1️⃣ KTX / KTX-산천만 예약
2️⃣ 모든 열차 포함

숫자를 입력하세요: 1 또는 2
"""

    REQUEST_SEAT_TYPE = """✅ 열차 종류 선택 완료

💺 좌석 종류를 선택해주세요.

1️⃣ 일반실 우선
2️⃣ 일반실만
3️⃣ 특실 우선
4️⃣ 특실만

숫자를 입력하세요: 1, 2, 3, 4
"""

    REQUEST_PASSENGER_COUNT = """✅ 좌석 종류 선택 완료

👥 탑승 인원수를 입력해주세요.

💡 1~9명까지 선택 가능합니다.
(현재는 성인 인원수만 지원합니다)

예) 2명이 탑승하는 경우: 2
"""

    REQUEST_SEAT_STRATEGY = """✅ 인원수 입력 완료 (총 {count}명)

🪑 좌석 배치 방식을 선택해 주십시오.

━━━━━━━━━━━━━━━━━━━━
1️⃣ 연속 좌석 (권장)
   • 같이 앉을 수 있도록 연속된 좌석 예약
   • 연속된 좌석이 없으면 예약 실패

2️⃣ 랜덤 배치
   • 한 자리씩 개별적으로 예약
   • 좌석이 떨어져 있을 수 있음
   • 예약 성공률이 더 높음
━━━━━━━━━━━━━━━━━━━━

숫자를 입력하세요: 1 또는 2
"""

    CONFIRM_RESERVATION = """✅ 모든 정보 입력 완료!

📋 예약 정보 확인
━━━━━━━━━━━━━━━━━━━━
📅 출발일: {depDate}
🚉 출발역: {srcLocate}
🏁 도착역: {dstLocate}
🕐 검색 시작: {depTime}
⏰ 검색 종료: {maxDepTime}
🚄 열차: {trainTypeShow}
💺 좌석: {specialInfoShow}
👥 인원: {passengerCount}명
🪑 배치: {seatStrategy}
━━━━━━━━━━━━━━━━━━━━

• Y 또는 예 → 예약 시작
• N 또는 아니오 → 작업 취소

⏱ 예약 완료까지 시간이 걸릴 수 있습니다.
"""

    RESERVATION_STARTED = """🎯 예약 검색을 시작합니다!

🔍 매진된 자리에 공석이 생길 때까지 계속 확인합니다.
✅ 예약 성공 시 즉시 알려드립니다!

💡 진행 중인 예약을 취소하려면 /cancel을 입력하세요.
"""

    ALREADY_RUNNING = """⚠️ 이미 예약이 진행 중입니다.

📋 진행 중인 예약 정보
━━━━━━━━━━━━━━━━━━━━
📅 출발일: {depDate}
🚉 출발역: {srcLocate}
🏁 도착역: {dstLocate}
🕐 검색 시작: {depTime}
🚄 열차: {trainTypeShow}
💺 좌석: {specialInfoShow}
━━━━━━━━━━━━━━━━━━━━

💡 예약을 취소하려면 /cancel을 입력하세요.
"""

    # ========== 에러 메시지 ==========
    ERROR_GENERIC = "⚠️ 오류가 발생했습니다.\n/cancel 또는 /start로 다시 시작해주세요."
    ERROR_INVALID_COMMAND = "❌ 알 수 없는 명령어입니다.\n/help로 사용 가능한 명령어를 확인하세요."
    ERROR_NO_PROGRESS = "ℹ️ 진행 중인 예약이 없습니다.\n/start를 입력하여 예약을 시작하세요."
    ERROR_PHONE_FORMAT = "❌ 전화번호 형식이 올바르지 않습니다.\n하이픈(-)을 포함하여 다시 입력해주세요.\n예시: 010-1234-5678"
    ERROR_DATE_FORMAT = """❌ 날짜 형식이 올바르지 않습니다.

8자리 숫자로 입력해주세요.
예시: 20250425 (2025년 4월 25일)

⚠️ 과거 날짜는 입력할 수 없습니다.
"""
    ERROR_TIME_FORMAT = "❌ 시간 형식이 올바르지 않습니다.\nHHMM 형식 4자리로 입력해주세요.\n예시: 1430 (오후 2시 30분)"
    ERROR_TRAIN_TYPE_INVALID = "❌ 1 또는 2를 입력해주세요."
    ERROR_SEAT_TYPE_INVALID = "❌ 1, 2, 3, 4 중 하나를 입력해주세요."
    ERROR_PASSENGER_COUNT_NOT_DIGIT = "❌ 숫자를 입력해주세요. (1~9)"
    ERROR_PASSENGER_COUNT_RANGE = "❌ 1~9명 사이의 인원수를 입력해주세요."
    ERROR_SEAT_STRATEGY_INVALID = "❌ 1 또는 2를 입력해주세요."
    ERROR_CONFIRM_INVALID = """❌ 올바른 응답을 입력해주세요.

• Y 또는 예 → 예약 시작
• N 또는 아니오 → 작업 취소
"""
    ERROR_ADMIN_ENV = "⚠️ 서버 환경변수가 설정되지 않았습니다."
    ERROR_ADMIN_LOGIN = "⚠️ 관리자 계정 로그인에 실패했습니다."
    ERROR_RESERVATION_START_FAILED = "❌ 예약 프로세스 시작에 실패했습니다.\n다시 시도해주세요."
    ERROR_NOT_SUBSCRIBER = """⚠️ 구독이 필요한 서비스입니다.

2024년부터 본 서비스가 유료화되었습니다.
구독을 원하시면 텔레그램 @dubidum으로 문의해주세요.

예약을 취소합니다.
"""
    # ========== 취소 및 완료 메시지 ==========
    CANCELLED = "✅ 예약이 취소되었습니다."
    CANCELLED_BY_USER = "🚫 예약을 취소합니다."
    CANCEL_START_CONFIRMATION = "🚫 예매 진행을 취소합니다."

    PAYMENT_REMINDER_STOPPED = """✅ 결제 리마인더가 중단되었습니다.

결제를 완료하셨다면 즐거운 여행 되세요! 🚄
아직 결제하지 않으셨다면 서둘러 결제를 완료해주세요.
"""

    PAYMENT_REMINDER_TIMEOUT = """⏰ 결제 리마인더 종료

예약 후 10분이 경과하여 리마인더가 자동 종료되었습니다.
결제를 완료하지 않으셨다면 예약이 취소되었을 수 있습니다.

💡 코레일 사이트에서 예약 상태를 확인해주세요.
"""

    # ========== 관리자 메시지 ==========
    ADMIN_AUTH_REQUIRED = "🔐 관리자 인증이 필요합니다.\n관리자 비밀번호를 입력해주세요."
    ADMIN_AUTH_SUCCESS = "✅ 관리자 인증 성공!"
    ADMIN_AUTH_FAILED = "❌ 관리자 인증 실패\n올바른 비밀번호를 입력해주세요."

    # ========== Backward Compatibility Methods for MessageTemplates ==========
    # These methods provide compatibility with the old MessageTemplates interface

    @staticmethod
    def welcome_message():
        """Welcome message (compatibility method)"""
        return Messages.WELCOME

    @staticmethod
    def request_phone_number():
        """Request phone number (compatibility method)"""
        return Messages.REQUEST_PHONE

    @staticmethod
    def request_password():
        """Request password (compatibility method)"""
        return Messages.REQUEST_PASSWORD

    @staticmethod
    def login_success():
        """Login success (compatibility method)"""
        return Messages.LOGIN_SUCCESS

    @staticmethod
    def login_failure(username: str):
        """Login failure (compatibility method)"""
        return Messages.LOGIN_FAILED_RETRY.format(username=username)

    @staticmethod
    def request_departure_station():
        """Request departure station after date input (compatibility method)"""
        return Messages.REQUEST_DATE

    @staticmethod
    def request_arrival_station():
        """Request arrival station after departure station input (compatibility method)"""
        return Messages.REQUEST_SRC_STATION

    @staticmethod
    def not_in_allow_list():
        """Not in allow list (compatibility method)"""
        return Messages.ERROR_NOT_SUBSCRIBER

    @staticmethod
    def reservation_started():
        """Reservation started (compatibility method)"""
        return Messages.RESERVATION_STARTED

    @staticmethod
    def reservation_cancelled():
        """Reservation cancelled (compatibility method)"""
        return Messages.CANCELLED

    @staticmethod
    def help_message():
        """Help message (compatibility method)"""
        return Messages.HELP

    @staticmethod
    def payment_reminder(remaining_minutes: int, remaining_seconds: int):
        """Payment reminder (compatibility method)"""
        if remaining_seconds == 0:
            time_text = f"{remaining_minutes}분"
        else:
            time_text = f"{remaining_minutes}분 {remaining_seconds}초"

        return f"""⏰ 결제 리마인더

예약 취소까지 남은 시간: {time_text}

서둘러 결제를 완료해주세요!
💡 결제 완료 후 아무 메시지나 입력하면 알림이 중단됩니다.
"""


class MessageService:
    """메시지 전송 서비스"""

    def __init__(self, session, send_url):
        """
        Args:
            session: requests.session() 객체
            send_url: 텔레그램 API URL
        """
        self.session = session
        self.send_url = send_url

    def send(self, chat_id, message):
        """
        메시지 전송

        Args:
            chat_id: 채팅 ID
            message: 전송할 메시지 (str 또는 템플릿 메서드)
        """
        url = f"{self.send_url}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": message
        }
        self.session.get(url, params=params)

    def send_to_multiple(self, chat_ids, message):
        """
        여러 사용자에게 메시지 전송

        Args:
            chat_ids: 채팅 ID 리스트
            message: 전송할 메시지
        """
        for chat_id in chat_ids:
            self.send(chat_id, message)
