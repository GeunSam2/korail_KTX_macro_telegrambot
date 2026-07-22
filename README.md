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

## 텔레그램 없이 로컬에서 실행

`local_cli.py`는 예약 성공/실패를 Windows 대화상자(WSL), Linux 데스크톱 알림,
터미널 소리와 `local_notifications.log`로 알립니다. 비밀번호는 프롬프트에서만 받으며
파일이나 명령 기록에 저장하지 않습니다.

```bash
python src/local_cli.py \\
  --from 서울 --to 부산 --date 20260801 \\
  --after 0900 --before 1200 --passengers 1
```

`--help`로 일반실/특실 우선순위, KTX 외 열차, 인원수 옵션을 확인할 수
있습니다. 조회 간격은 기본 1초이며 더 짧게 설정하지 마세요.

자격정보 파일은 1행에 코레일 회원번호, 2행에 비밀번호를 넣고
`--credentials-file` 옵션으로 지정할 수 있습니다. 해당 파일은 Git 저장소 밖에
보관하세요.

## Windows GUI

GUI 버전은 코레일 계정, 역, 날짜, 시간, 좌석 옵션을 화면에서 설정하고
예약 루프를 시작·중지할 수 있습니다. 예약 성공 시 Windows 팝업과 소리를
제공하며, Google OAuth로 Gmail을 연결하면 성공·치명적 오류 알림을
지정한 수신 이메일로 발송합니다. Google 비밀번호를 앱에 입력할 필요가
없으며 `gmail.send` 발신 권한과 계정 이메일 확인 권한만
요청합니다. 최초 연동 시 Google Cloud에서 생성한 데스크톱 앱 OAuth JSON이
필요하며, 승인 토큰은 Windows 자격 증명 관리자에 저장됩니다.

배포용으로는 개발자의 프로덕션 데스크톱 OAuth JSON을 EXE와 같은 폴더에
`oauth_client.json`으로 두면 됩니다. 이 경우 각 사용자는 Google Cloud를 설정할 필요 없이
브라우저에서 자신의 Google 계정으로 로그인하고 권한만 승인합니다. 테스트 상태의
OAuth 앱은 최대 100명의 테스트 사용자를 명시해야 하며 Gmail 권한이 포함된 승인은
7일 후 만료됩니다. 일반 배포 전에는 OAuth 브랜딩·데이터 액세스 검증을 완료하세요.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

빌드 결과는 `dist\KTX 자동예약\KTX 자동예약.exe`입니다. 배포할 때는
`KTX 자동예약` 폴더 전체를 압축하세요.

## 참고

- 본 서비스는 [carpedm20/korail2](https://github.com/carpedm20/korail2)를 기반으로 합니다.
- Dynapath 우회 패치가 적용된 [dhfhfk/korail2](https://github.com/dhfhfk/korail2/tree/bypassDynapath) fork를 패키지로 설치하여 사용합니다.

## 주의사항

1. 귀경길 기차 예매를 하지 못한 안타까운 영혼들을 위해 만든 프로그램이므로, 개인용 목적이 아닌 상업적 목적등으로 이용하는 것을 엄중히 금합니다.
2. 본 프로그램을 사용할 경우, 기본으로 설정된 1초에 1번 조회 요청에 대한 설정 값 이상으로 빠르게 설정하지 마십시오. 코레일 서버에 무리가 갈 뿐 아니라, 단위 시간내에 보다 빠른 값으로 조회를 요청할 경우, 계정이 정지될 수 있습니다.
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
  - korail2 라이브러리 import 확인
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

### korail2 라이브러리 업데이트
```bash
# 최신 버전으로 업데이트
pipenv update korail2

# requirements.txt 재생성
make requirements
```

## 프로젝트 구조

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
- **Korail API**: [dhfhfk/korail2](https://github.com/dhfhfk/korail2/tree/bypassDynapath)
- **Testing**: pytest
- **Deployment**: Docker
