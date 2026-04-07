# Redis + Docker Compose 업그레이드 계획

## 📋 목차
- [현재 상황 분석](#현재-상황-분석)
- [업그레이드 목표](#업그레이드-목표)
- [구현 계획](#구현-계획)
- [데이터 마이그레이션 전략](#데이터-마이그레이션-전략)
- [구현 단계별 체크리스트](#구현-단계별-체크리스트)
- [주의사항](#주의사항)
- [추가 개선 아이디어](#추가-개선-아이디어)

---

## 🔍 현재 상황 분석

### 현재 아키텍처
- ✅ Storage Interface 패턴 이미 구현됨 ([src/storage/base.py](src/storage/base.py))
- ✅ InMemoryStorage 구현체 존재 ([src/storage/memory.py](src/storage/memory.py))
- ❌ 재시작 시 모든 데이터 손실
- ❌ 단일 컨테이너로 배포 (Redis 없음)
- ❌ docker run 명령어로 수동 배포

### 저장되는 데이터
1. `UserSession` - 사용자 대화 상태 (로그인 정보, 진행 단계, 열차 검색 정보)
2. `RunningReservation` - 실행 중인 예약 프로세스
3. `PaymentStatus` - 결제 리마인더 상태
4. `Subscribers` - 알림 구독자 목록

---

## 🎯 업그레이드 목표

1. **Redis 도입**: 인메모리 데이터를 Redis로 영구 저장
2. **Docker Compose**: 멀티 컨테이너 오케스트레이션
3. **볼륨 퍼시스턴스**: Redis 데이터 로컬 볼륨에 저장
4. **CI/CD 개선**: GitHub Actions에서 docker-compose 활용

---

## 📐 구현 계획

### Phase 1: Redis Storage 구현

#### 1.1 Redis Storage Adapter 작성
파일: `src/storage/redis.py`

```python
class RedisStorage(StorageInterface):
    """Redis-based persistent storage"""

    # Key patterns:
    # - user_session:{chat_id} → JSON
    # - running_reservation:{chat_id} → JSON
    # - payment_status:{chat_id} → JSON
    # - subscribers → Set
```

**데이터 직렬화 전략:**
- Dataclass → JSON으로 직렬화
- datetime 필드 → ISO 8601 문자열
- Redis TTL 활용 (선택적)

#### 1.2 Dependencies 추가
`requirements.txt`에 추가:
```txt
redis==5.0.1
hiredis==2.3.2  # Performance boost
```

#### 1.3 환경 변수 추가
`.env.default`에 추가:
```bash
# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Optional

# Storage Type Selection
STORAGE_TYPE=redis  # or 'memory'
```

---

### Phase 2: Docker Compose 구성

#### 2.1 docker-compose.yml 생성
```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: korailreserve
    ports:
      - "8000:8080"
    environment:
      - BOTTOKEN=${BOTTOKEN}
      - USERID=${USERID}
      - USERPW=${USERPW}
      - ALLOW_LIST=${ALLOW_LIST}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      - STORAGE_TYPE=redis
    depends_on:
      - redis
    restart: always
    networks:
      - korail_network

  redis:
    image: redis:7-alpine
    container_name: korailreserve_redis
    ports:
      - "6379:6379"  # Optional: for debugging
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: always
    networks:
      - korail_network

volumes:
  redis_data:
    driver: local

networks:
  korail_network:
    driver: bridge
```

#### 2.2 docker-compose.prod.yml (프로덕션 오버라이드)
```yaml
version: '3.8'

services:
  app:
    image: geunsam2/korailbot:latest
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}

  redis:
    # Redis password 추가
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```

---

### Phase 3: CI/CD 업그레이드

#### 3.1 새로운 GitHub Actions Workflow
파일: `.github/workflows/cicd.yml`

```yaml
name: Build and Deploy with Docker Compose

on:
  push:
    branches: ['master']
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64
          push: true
          tags: geunsam2/korailbot:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy with Docker Compose
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: server.geunsam2.xyz
          username: ${{ secrets.SSH_USERNAME }}
          password: ${{ secrets.SSH_PASSWORD }}
          port: 22
          script: |
            # Create directory if not exists
            mkdir -p ~/korailbot
            cd ~/korailbot

            # Create .env file
            cat > .env << EOF
            BOTTOKEN=${{ secrets.TELEGRAM_BOTTOKEN }}
            USERID=${{ secrets.ADMIN_USERID }}
            USERPW=${{ secrets.ADMIN_PASSWD }}
            ALLOW_LIST=${{ vars.ALLOW_LIST }}
            REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}
            EOF

            # Download docker-compose files
            curl -o docker-compose.yml https://raw.githubusercontent.com/GeunSam2/korail_KTX_macro_telegrambot/master/docker-compose.yml
            curl -o docker-compose.prod.yml https://raw.githubusercontent.com/GeunSam2/korail_KTX_macro_telegrambot/master/docker-compose.prod.yml

            # Pull latest images
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

            # Recreate containers
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate

            # Cleanup old images
            docker image prune -f
```

#### 3.2 필요한 GitHub Secrets
- `REDIS_PASSWORD` (새로 추가)
- `DOCKERHUB_USERNAME` (기존)
- `DOCKERHUB_TOKEN` (기존)
- `TELEGRAM_BOTTOKEN` (기존)
- `ADMIN_USERID` (기존)
- `ADMIN_PASSWD` (기존)
- `SSH_USERNAME` (기존)
- `SSH_PASSWORD` (기존)

---

### Phase 4: Storage Factory 패턴

#### 4.1 스토리지 선택 로직
파일: `src/storage/__init__.py`

```python
from storage.base import StorageInterface
from config.settings import settings

def create_storage() -> StorageInterface:
    """Create storage based on environment configuration."""
    storage_type = settings.STORAGE_TYPE  # 'memory' or 'redis'

    if storage_type == 'redis':
        from storage.redis import RedisStorage
        return RedisStorage(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )
    else:
        from storage.memory import InMemoryStorage
        return InMemoryStorage()

# For backward compatibility
InMemoryStorage = create_storage
```

#### 4.2 Settings 업데이트
파일: `src/config/settings.py`

```python
class Settings:
    # ... existing settings ...

    # Redis Configuration
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD: Optional[str] = os.getenv('REDIS_PASSWORD')

    # Storage Type Selection
    STORAGE_TYPE: str = os.getenv('STORAGE_TYPE', 'memory')
```

---

## 📊 데이터 마이그레이션 전략

### Zero-Downtime 배포
1. 기존 데이터는 재시작 시 손실 (현재 동작과 동일)
2. Redis 도입 후부터 데이터 영구 저장
3. 점진적 전환 가능: `STORAGE_TYPE=memory` → `STORAGE_TYPE=redis`

### Redis 데이터 스키마
```
user_session:{chat_id}           → JSON string (UserSession)
running_reservation:{chat_id}    → JSON string (RunningReservation)
payment_status:{chat_id}         → JSON string (PaymentStatus)
subscribers                      → Set<int> (chat_id들)
```

### 데이터 직렬화 예시
```python
# UserSession 저장
session_json = {
    "chat_id": 123456789,
    "in_progress": true,
    "last_action": 5,
    "credentials": {
        "korail_id": "010-1234-5678",
        "korail_pw": "encrypted_password"
    },
    "train_info": {...},
    "process_id": 9999999
}
redis.set("user_session:123456789", json.dumps(session_json))
```

---

## 🔧 구현 단계별 체크리스트

### ✅ Phase 1: Redis Storage (Week 1)
- [ ] RedisStorage 클래스 구현
  - [ ] `__init__` 및 연결 설정
  - [ ] UserSession CRUD 메소드
  - [ ] RunningReservation CRUD 메소드
  - [ ] PaymentStatus CRUD 메소드
  - [ ] Subscribers 관리 메소드
- [ ] JSON 직렬화/역직렬화 헬퍼 함수
  - [ ] Dataclass → JSON
  - [ ] JSON → Dataclass
  - [ ] datetime 처리
- [ ] Redis 연결 헬스체크
- [ ] Storage Factory 패턴 적용
- [ ] 환경 변수 설정 (settings.py)
- [ ] 단위 테스트 작성
  - [ ] RedisStorage 기능 테스트
  - [ ] 직렬화/역직렬화 테스트

### ✅ Phase 2: Docker Compose (Week 1-2)
- [ ] `docker-compose.yml` 작성
  - [ ] app 서비스 정의
  - [ ] redis 서비스 정의
  - [ ] 네트워크 구성
  - [ ] 볼륨 설정
- [ ] `docker-compose.prod.yml` 작성
  - [ ] 프로덕션 이미지 사용
  - [ ] Redis 비밀번호 설정
  - [ ] 포트 매핑 조정
- [ ] 로컬 테스트
  - [ ] `docker-compose up` 실행
  - [ ] 앱-Redis 연결 확인
  - [ ] 데이터 저장/조회 테스트
- [ ] `.dockerignore` 업데이트

### ✅ Phase 3: CI/CD (Week 2)
- [ ] GitHub Actions 워크플로우 업데이트
  - [ ] Build and Push 단계
  - [ ] Deploy 단계 (docker-compose 사용)
- [ ] SSH 배포 스크립트 작성
  - [ ] .env 파일 생성
  - [ ] docker-compose 파일 다운로드
  - [ ] 컨테이너 재시작
- [ ] GitHub Secrets 추가
  - [ ] REDIS_PASSWORD
- [ ] 롤백 전략 수립
  - [ ] 이전 이미지 태그 보관
  - [ ] 수동 롤백 절차 문서화

### ✅ Phase 4: 검증 & 문서화 (Week 2)
- [ ] 통합 테스트
  - [ ] 전체 예약 플로우 테스트
  - [ ] 재시작 후 데이터 복구 확인
- [ ] 모니터링 설정
  - [ ] Redis 메모리 사용량 확인
  - [ ] 로그 확인 (docker-compose logs)
- [ ] 문서화
  - [ ] README 업데이트
  - [ ] 배포 가이드 작성
  - [ ] 트러블슈팅 가이드
- [ ] 성능 테스트
  - [ ] Redis 응답 속도
  - [ ] 메모리 사용량

---

## ⚠️ 주의사항

### 1. 하위 호환성
- `STORAGE_TYPE=memory`로 기존 방식 유지 가능
- Redis 미설치 환경에서도 동작해야 함
- 점진적 마이그레이션 가능

### 2. Redis 장애 대응
- Redis 다운 시 앱이 시작 안 됨 → health check 필요
- Redis 연결 실패 시 재시도 로직
- Fallback to memory storage (선택사항)

### 3. 데이터 백업
- Redis RDB 파일 주기적 백업
- AOF(Append Only File) 활성화로 데이터 손실 최소화
- 백업 스크립트 작성 (cron)

### 4. 보안
- Redis password 필수 (프로덕션)
- Redis 포트 외부 노출 최소화
- 민감 정보 암호화 (korail_pw 등)

### 5. 메모리 관리
- Redis `maxmemory` 정책 설정
  - 권장: `allkeys-lru` (LRU eviction)
- 예상 메모리 사용량 계산
  - UserSession: ~2KB/user
  - 100 users = ~200KB
  - 여유있게 256MB 할당

### 6. 네트워크
- Docker 네트워크 격리
- Redis는 내부 네트워크만 접근 가능
- 필요시 Redis Sentinel/Cluster 고려

---

## 💡 추가 개선 아이디어

### 단기 개선 (Optional)
1. **Redis Commander**: Redis GUI 툴 추가 (디버깅용)
   ```yaml
   redis-commander:
     image: rediscommander/redis-commander:latest
     environment:
       - REDIS_HOSTS=local:redis:6379
     ports:
       - "8081:8081"
   ```

2. **Health Check 엔드포인트**
   ```python
   @app.route('/health')
   def health_check():
       return {
           "status": "healthy",
           "redis": redis_client.ping(),
           "storage_type": settings.STORAGE_TYPE
       }
   ```

3. **Data Export 기능**: Redis 데이터를 JSON으로 내보내기

### 중장기 개선
1. **Redis Sentinel**: HA(High Availability) 구성
2. **Monitoring Stack**:
   - Redis Exporter
   - Prometheus
   - Grafana 대시보드
3. **Centralized Logging**:
   - ELK Stack 또는 Loki
4. **Auto-scaling**: 부하에 따른 자동 확장

---

## 📚 참고 자료

### Redis
- [Redis Documentation](https://redis.io/docs/)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Redis Persistence](https://redis.io/docs/management/persistence/)

### Docker Compose
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Compose File Reference](https://docs.docker.com/compose/compose-file/)

### Best Practices
- [Redis Best Practices](https://redis.io/docs/management/optimization/)
- [Docker Compose in Production](https://docs.docker.com/compose/production/)

---

## 🔄 마이그레이션 타임라인

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 1 | Phase 1 | Redis Storage 구현 | RedisStorage 클래스, 테스트 |
| 1-2 | Phase 2 | Docker Compose 구성 | docker-compose.yml, 로컬 테스트 |
| 2 | Phase 3 | CI/CD 업데이트 | GitHub Actions 워크플로우 |
| 2 | Phase 4 | 검증 & 문서화 | 통합 테스트, 문서 |

**예상 소요 시간**: 2주 (파트타임 기준)

---

## ✅ 완료 기준

- [ ] Redis에 데이터가 정상적으로 저장/조회됨
- [ ] 컨테이너 재시작 후 데이터 유지됨
- [ ] docker-compose로 전체 스택 실행 가능
- [ ] CI/CD 파이프라인이 자동으로 배포됨
- [ ] 프로덕션 환경에서 안정적으로 동작
- [ ] 문서화 완료 (README, 배포 가이드)

---

**작성일**: 2026-04-08
**작성자**: Claude Code Assistant
**문서 버전**: 1.0
