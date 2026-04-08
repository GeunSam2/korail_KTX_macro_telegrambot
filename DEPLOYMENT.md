# 🚀 Deployment Guide

## 서버 초기 설정 (최초 1회만)

### 1. Docker 및 Docker Compose 설치

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치 (V2)
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 사용자를 docker 그룹에 추가 (재로그인 필요)
sudo usermod -aG docker $USER

# 확인
docker --version
docker compose version
```

### 2. 작업 디렉토리 생성

```bash
mkdir -p ~/korail_bot
cd ~/korail_bot
```

### 3. docker-compose.yml 복사

GitHub Actions가 자동으로 복사하지만, 수동으로도 가능합니다:

```bash
# 로컬에서 서버로 복사
scp docker-compose.yml user@server:/home/user/korail_bot/

# 또는 서버에서 직접 다운로드
wget https://raw.githubusercontent.com/your-repo/master/docker-compose.yml
```

### 4. .env 파일 생성

```bash
cd ~/korail_bot

# .env 파일 생성
cat > .env << 'EOF'
BOTTOKEN=your_telegram_bot_token
USERID=your_korail_id
USERPW=your_korail_password
ALLOW_LIST=010-1234-5678
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
EOF

# 권한 설정 (보안)
chmod 600 .env
```

---

## 🔄 배포 (자동)

코드를 master 브랜치에 push하면 **GitHub Actions가 자동으로 배포**합니다:

```bash
git push origin master
```

배포 과정:
1. ✅ Docker 이미지 빌드
2. ✅ DockerHub에 푸시
3. ✅ 서버에 docker-compose.yml 복사
4. ✅ 서버에 .env 파일 생성
5. ✅ 최신 이미지 다운로드
6. ✅ docker-compose up -d 실행

---

## 🛠 수동 배포 (필요시)

### 서버에서 직접 실행

```bash
cd ~/korail_bot

# 최신 이미지 다운로드
docker pull geunsam2/korailbot:latest

# 컨테이너 재시작
docker-compose down
docker-compose up -d

# 상태 확인
docker-compose ps
docker-compose logs -f
```

---

## 📊 모니터링

### 서비스 상태 확인

```bash
cd ~/korail_bot

# 컨테이너 상태
docker-compose ps

# 실시간 로그
docker-compose logs -f

# 앱 로그만
docker-compose logs -f app

# Redis 로그만
docker-compose logs -f redis

# 최근 50줄
docker-compose logs --tail=50
```

### Redis 데이터 확인

```bash
# Redis CLI 접속
docker exec -it korail_redis redis-cli

# 명령어
> PING                          # 연결 테스트
> DBSIZE                        # 총 키 개수
> KEYS *                        # 모든 키 보기
> GET user_session:123456       # 특정 데이터 보기
> INFO memory                   # 메모리 사용량
> EXIT
```

### 헬스체크

```bash
# 앱 헬스체크
curl http://localhost:8000/

# Redis 헬스체크
docker exec korail_redis redis-cli PING
```

---

## 🔧 관리 명령어

### 서비스 제어

```bash
# 시작
docker-compose up -d

# 중지
docker-compose down

# 재시작
docker-compose restart

# 앱만 재시작
docker-compose restart app

# Redis만 재시작
docker-compose restart redis
```

### 데이터 관리

```bash
# Redis 데이터 백업 (RDB 파일)
docker exec korail_redis redis-cli BGSAVE
docker cp korail_redis:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb

# 모든 데이터 삭제 (주의!)
docker exec korail_redis redis-cli FLUSHDB

# 컨테이너 및 볼륨 완전 삭제 (주의!)
docker-compose down -v
```

### 이미지 업데이트

```bash
# 최신 이미지 다운로드
docker pull geunsam2/korailbot:latest

# 기존 컨테이너 삭제 후 재시작
docker-compose up -d --force-recreate
```

---

## 🐛 트러블슈팅

### 앱이 시작 안됨

```bash
# 로그 확인
docker-compose logs app

# Redis 연결 확인
docker exec korail_redis redis-cli PING

# 환경 변수 확인
docker-compose config

# 포트 충돌 확인
sudo netstat -tlnp | grep 8000
```

### Redis 메모리 부족

```bash
# 메모리 사용량 확인
docker exec korail_redis redis-cli INFO memory

# 불필요한 키 삭제
docker exec korail_redis redis-cli FLUSHDB

# Redis 재시작
docker-compose restart redis
```

### 컨테이너가 계속 재시작됨

```bash
# 상세 로그 확인
docker-compose logs --tail=100 app

# 컨테이너 상태 확인
docker inspect korail_bot

# 환경 변수 문제일 가능성
cat .env
```

---

## 🔐 보안 권장사항

### .env 파일 보호

```bash
# 파일 권한 제한
chmod 600 .env

# 소유자 확인
ls -la .env
```

### Redis 비밀번호 설정 (선택)

```bash
# .env에 추가
echo "REDIS_PASSWORD=your_strong_password" >> .env

# docker-compose.yml 수정 필요 (Redis command에 --requirepass 추가)
```

### 방화벽 설정

```bash
# Redis 포트는 외부 접근 차단 (Docker 네트워크 내부만)
sudo ufw allow 8000/tcp     # 앱만 허용
sudo ufw deny 6379/tcp      # Redis는 차단
```

---

## 📈 성능 튜닝

### Redis 설정 조정

docker-compose.yml에서 수정:

```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb              # 메모리 제한 증가
    --maxmemory-policy allkeys-lru
    --save 300 10                # 5분마다 10개 이상 변경시 저장
```

### 로그 로테이션

```bash
# Docker 로그 크기 제한
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

sudo systemctl restart docker
```

---

## 📞 Support

문제 발생 시:
1. 로그 확인: `docker-compose logs -f`
2. Redis 상태: `docker exec korail_redis redis-cli PING`
3. 이슈 등록: GitHub Issues
4. 문서 참조: REDIS_MIGRATION.md

---

## 🔄 업데이트 체크리스트

새 버전 배포 시:
- [ ] GitHub에 push (자동 배포)
- [ ] 서버에서 로그 확인
- [ ] 헬스체크 실행
- [ ] Redis 데이터 확인
- [ ] 테스트 예약 실행
