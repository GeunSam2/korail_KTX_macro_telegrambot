# 코레일 KTX 예매 텔레그램 챗봇

매진된 KTX 열차를 자동으로 모니터링하여 좌석이 나오면 예약해주는 텔레그램 봇입니다.

## 빠른 시작

```bash
# 프로젝트 클론
git clone https://github.com/GeunSam2/korail_KTX_macro_telegrambot.git
cd korail_KTX_macro_telegrambot

# 의존성 설치 및 실행
make setup       # 처음 한 번만 (pipenv 설치)
make install     # 패키지 설치
make run         # 실행
```

## 참고

- 코레일 API 클라이언트로 [devgyurak/pykorail](https://github.com/devgyurak/pykorail)을 사용합니다 (코레일+ 7.0.8 규격, Python 3.10+).
- 과거에 사용했던 [carpedm20/korail2](https://github.com/carpedm20/korail2) 계열은 2026-09 코레일+ 앱 업데이트 이후 `-2000 이용 제한` 응답을 받아 동작하지 않습니다.
- 코레일은 AWS 등 데이터센터·VPN IP를 차단(`-8202`)하고, 매크로로 판정한 공인 IP도 차단합니다. 봇은 가정용 회선에서 실행하세요. 한 번 차단된 IP는 코드를 고쳐도 풀리지 않으며 공인 IP가 바뀌어야 합니다.
- DynaPath 기기 식별자는 `KORAIL_DEVICE_FILE`(기본 `~/.korail_bot_device.json`)에 저장되어 모든 프로세스가 같은 기기로 보이게 합니다. 고정하려면 `KORAIL_DEVICE_PROFILE_ID`/`KORAIL_ANDROID_ID`를 환경변수로 지정하세요.

## 주의사항

1. 귀경길 기차 예매를 하지 못한 안타까운 영혼들을 위해 만든 프로그램이므로, 개인용 목적이 아닌 상업적 목적등으로 이용하는 것을 엄중히 금합니다.
2. 본 프로그램을 사용할 경우, 기본으로 설정된 3초에 1번(`SEARCH_INTERVAL=3`) 조회 요청보다 빠르게 설정하지 마십시오. 짧은 조회 간격은 매크로 판정과 IP 차단의 주된 원인입니다. 코레일 서버에 무리가 갈 뿐 아니라, 단위 시간내에 보다 빠른 값으로 조회를 요청할 경우, 계정이 정지될 수 있습니다.
3. 본 프로그램은 2026-04-08일 기준으로 정상 동작하지만, 사이트의 구성이나 변수명 변경등에 따라 언제든 동작하지 않을 수 있습니다.

## 설정법

### 로컬 개발 (macOS/Linux)

#### 방법 1: mise 사용 (권장)

```bash
# 1. mise 설치 (없는 경우)
brew install mise

# 2. 환경 변수 설정
cp .env.default .env
# .env 파일을 열어서 BOTTOKEN 등 실제 값으로 수정

# 3. mise 활성화 (자동으로 .env.default와 .env 로드)
mise trust
mise install

# 4. 의존성 설치 및 실행
pipenv install
pipenv run python src/app.py
```

**mise 환경변수 로딩 순서:**
1. `.env.default` - 기본값 (git에 커밋됨)
2. `.env` - 로컬 오버라이드 (git에 커밋되지 않음)

#### 방법 2: pipenv 직접 사용

```bash
# 1. 개발 환경 설정 (처음 한 번만)
make setup         # pipenv, pyenv 설치 (없는 경우)

# 2. 환경 변수 설정
export BOTTOKEN=your_telegram_bot_token

# 3. 의존성 설치
make install       # pipenv install 실행

# 4. 실행
make run           # 애플리케이션 실행

# 또는 쉘에 진입하여 실행
make shell         # pipenv shell 실행
python src/app.py
```

**사용 가능한 명령어:**
- `make help` - 사용 가능한 명령어 목록 확인
- `make setup` - 개발 환경 설정
- `make install` - 의존성 설치
- `make run` - 애플리케이션 실행
- `make shell` - pipenv shell 진입
- `make test` - 전체 테스트 실행
- `make test-api` - API 엔드포인트 테스트만 실행
- `make test-logic` - Korail 로직 테스트만 실행
- `make requirements` - requirements.txt 생성

### Docker 배포

```bash
# 1. requirements.txt 생성 (Pipfile에서)
make requirements

# 2. Docker 이미지 빌드
make build

# 3. 실행
docker run -dit \
  -e BOTTOKEN=[텔레그램봇토큰] \
  -e ALLOW_LIST=[허용할전화번호목록] \
  -p 8080:8080 \
  geunsam2/korailbot:v3

# 또는 (관리자 편의 로그인 사용)
docker run -dit \
  -e BOTTOKEN=[텔레그램봇토큰] \
  -e ALLOW_LIST=[허용할전화번호목록] \
  -e USERID=[코레일ID] \
  -e USERPW=[코레일비밀번호] \
  -p 8080:8080 \
  geunsam2/korailbot:v3
```

### 환경변수

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `BOTTOKEN` | ✅ | 텔레그램 봇 토큰 |
| `ALLOW_LIST` | ❌ | 허용할 사용자 전화번호 목록 (쉼표로 구분) |
| `USERID` | ❌ | 관리자 편의 로그인용 코레일 ID |
| `USERPW` | ❌ | 관리자 편의 로그인용 코레일 비밀번호 |

## 개발 워크플로우

### 테스트 실행

```bash
# 전체 테스트 실행
make test

# API 엔드포인트 테스트만 실행
make test-api

# Korail 로직 테스트만 실행
make test-logic
```

**테스트 구성:**
- `tests/test_api.py` - Flask API 엔드포인트 테스트
  - `/telebot` 엔드포인트 존재 확인
  - `/check_payment` 엔드포인트 존재 확인
  - CORS 헤더 확인
  - 404 에러 처리 확인

- `tests/test_korail_logic.py` - Korail 예약 로직 테스트
  - pykorail 라이브러리 import 확인
  - 필수 클래스 (Korail, TrainType, ReserveOption) 확인
  - Flask 및 Telegram Bot 의존성 확인
  - 결제 리마인더 시간 설정 (10분, 10초 간격) 확인

### 의존성 추가 시
```bash
# 1. Pipfile에 패키지 추가
pipenv install [패키지명]

# 2. requirements.txt 재생성 (Docker 배포용)
make requirements

# 3. 커밋
git add Pipfile Pipfile.lock requirements.txt
git commit -m "feat: Add new dependency"
```

### pykorail 라이브러리 업데이트

```bash
pipenv update pykorail
```
src/
├── app.py                          # Flask 앱 진입점
├── config/                         # 설정 관리
├── models/                         # 데이터 모델
├── services/                       # 비즈니스 로직
├── storage/                        # 상태 관리
├── handlers/                       # 요청 처리
├── api/                            # API 엔드포인트
├── utils/                          # 유틸리티
└── telegramBot/                    # 레거시 코드

tests/                              # 테스트
```

## 기술 스택

- **Backend**: Flask, Flask-RESTful, Flask-CORS
- **Telegram**: python-telegram-bot
- **Korail API**: [devgyurak/pykorail](https://github.com/devgyurak/pykorail)
- **Testing**: pytest
- **Deployment**: Docker
