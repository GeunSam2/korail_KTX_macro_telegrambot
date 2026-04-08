# Redis Migration Guide

## 🎯 Overview

This application has been migrated from in-memory storage to Redis-based persistent storage, enabling:
- ✅ Process-shared state (Flask app + background processes)
- ✅ Data persistence across restarts
- ✅ Complex multi-step flows (random seating with payment confirmation)
- ✅ Production-ready scalability

---

## 🚀 Quick Start

### Local Development

```bash
# Start Redis + App with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop everything
docker-compose down

# Stop and remove data
docker-compose down -v
```

### Environment Variables

Required:
```bash
BOTTOKEN=your_telegram_bot_token
USERID=korail_admin_id
USERPW=korail_password
```

Optional:
```bash
REDIS_HOST=localhost        # default: localhost
REDIS_PORT=6379             # default: 6379
REDIS_DB=0                  # default: 0
REDIS_PASSWORD=             # default: none
ALLOW_LIST=010-1234-5678    # comma-separated
```

---

## 📊 Redis Data Structure

### User Sessions
```
Key: user_session:{chat_id}
Type: String (JSON)
TTL: None (persistent)
Value: {
  chat_id, in_progress, last_action,
  credentials: {korail_id, korail_password},
  search_params: {dep_date, src_locate, ...}
}
```

### Running Reservations
```
Key: running_reservation:{chat_id}
Type: String (JSON)
TTL: None
Value: {chat_id, process_id, korail_id, search_params}
```

### Partial Reservations (Random Seating)
```
Key: partial_reservations:{chat_id}
Type: String (JSON Array)
TTL: 2 hours
Value: [{seat_index, train_info, reserved_at}, ...]
```

### Current Seat Index
```
Key: current_seat_index:{chat_id}
Type: String (integer)
TTL: 2 hours
Value: "0" | "1" | ...
```

### Payment Ready Flag
```
Key: payment_ready:{chat_id}:{seat_index}
Type: String
TTL: 60 seconds
Value: "1"
```

### Admin Authentication
```
Key: admin_authenticated:{chat_id}
Type: String
TTL: 1 hour
Value: "1"
```

### Subscribers
```
Key: subscribers
Type: Set
Value: {chat_id1, chat_id2, ...}
```

---

## 🔧 Redis CLI Commands

### Connect to Redis
```bash
# Via Docker
docker exec -it korail_redis redis-cli

# Local
redis-cli -h localhost -p 6379
```

### Useful Commands
```redis
# List all keys
KEYS *

# Get user session
GET user_session:123456

# Check current seat index
GET current_seat_index:123456

# Get partial reservations
GET partial_reservations:123456

# Check if payment ready
GET payment_ready:123456:0

# List all subscribers
SMEMBERS subscribers

# Clear all data (DANGEROUS!)
FLUSHDB

# View Redis info
INFO
DBSIZE
```

---

## 🎭 Random Seating Flow

### Phase 1: First Seat Reservation
```
Backend Process                Redis                    Main App (Webhook)
      |                         |                             |
      |-- SET current_seat:0 -->|                             |
      |-- Reserve seat 1     -->|                             |
      |-- SAVE partial_res:0 -->|                             |
      |-- Send callback ------->|-----> User gets message --->|
      |                         |                             |
      |-- WAIT (poll every 1s)->|                             |
      |-- GET payment_ready:0   |                             |
      |                         |<-- User: "결제완료" --------|
      |                         |<-- SET payment_ready:0 -----|
      |<- Flag detected! --------|                             |
      |                         |                             |
```

### Phase 2: Next Seat
```
Backend Process                Redis                    Main App
      |                         |                             |
      |-- SET current_seat:1 -->|                             |
      |-- Reserve seat 2     -->|                             |
      |-- SAVE partial_res:1 -->|                             |
      |-- Send callback ------->|-----> User gets message --->|
      |                         |                             |
      (repeat until all seats)
```

---

## 🐛 Troubleshooting

### Redis Connection Failed
```bash
# Check if Redis is running
docker-compose ps

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Lost Data After Restart
```bash
# Check if volume exists
docker volume ls | grep redis_data

# Check Redis persistence settings
docker exec -it korail_redis redis-cli CONFIG GET save

# Should see: "60 1000" (save every 60s if 1000+ keys changed)
```

### Memory Issues
```bash
# Check Redis memory usage
docker exec -it korail_redis redis-cli INFO memory

# Redis is configured with:
# maxmemory: 512mb
# maxmemory-policy: allkeys-lru (evict least recently used)
```

### Data Not Shared Between Processes
```bash
# Verify both processes connect to same Redis
docker-compose logs app | grep "Redis connected"
docker-compose logs app | grep "Redis storage"

# Should see same host:port in both
```

---

## 📈 Monitoring

### Key Metrics to Watch
```bash
# Total keys
redis-cli DBSIZE

# Memory usage
redis-cli INFO memory | grep used_memory_human

# Connections
redis-cli INFO clients | grep connected_clients

# Operations per second
redis-cli INFO stats | grep instantaneous_ops_per_sec
```

### Health Check
```bash
# Simple ping
redis-cli PING
# Should return: PONG

# Via Docker health check
docker inspect korail_redis | grep -A 5 Health
```

---

## 🔐 Security Notes

1. **Production**: Set `REDIS_PASSWORD` environment variable
2. **Network**: Redis is only accessible within Docker network by default
3. **Persistence**: Data is stored in Docker volume `redis_data`
4. **Backup**: Regular backups recommended for production

---

## 📚 Additional Resources

- [Redis Documentation](https://redis.io/docs/)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Docker Compose Docs](https://docs.docker.com/compose/)

---

## 🆘 Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify Redis connection: `docker exec -it korail_redis redis-cli PING`
3. Check environment variables: `docker-compose config`
4. Review this guide's troubleshooting section
