# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the Korail KTX Telegram Bot application. The tests are organized into three main categories:

- **Unit Tests**: Test individual functions and validators
- **Integration Tests**: Test service interactions and workflows
- **E2E Tests**: Test complete user journeys

**Total Tests: 119+**

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   └── test_validators.py  # Input validation tests (47 tests)
├── integration/            # Integration tests
│   ├── test_refactored_app.py       # Basic architecture tests (9 tests)
│   ├── test_conversation_handler.py # Conversation flow tests (18 tests)
│   ├── test_reservation_service.py  # Reservation management tests (8 tests)
│   ├── test_payment_reminder.py     # Payment reminder tests (11 tests)
│   └── test_webhook.py              # Webhook handling tests (15 tests)
├── e2e/                    # End-to-end tests
│   └── test_full_reservation_flow.py # Complete flows (7 tests)
└── conftest.py            # Shared fixtures (Redis container)
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pipenv install --dev

# Dependencies include:
# - pytest
# - pytest-cov (coverage reporting)
# - pytest-mock (mocking utilities)
# - pytest-asyncio (async test support)
# - freezegun (time manipulation)
# - testcontainers (Redis container for testing)
```

### Run All Tests

```bash
pipenv run pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pipenv run pytest tests/unit/ -v

# Integration tests only
pipenv run pytest tests/integration/ -v

# E2E tests only
pipenv run pytest tests/e2e/ -v
```

### Run Specific Test Files

```bash
# Validator tests
pipenv run pytest tests/unit/test_validators.py -v

# Conversation handler tests
pipenv run pytest tests/integration/test_conversation_handler.py -v

# Full flow tests
pipenv run pytest tests/e2e/test_full_reservation_flow.py -v
```

### Run Specific Tests

```bash
# Run single test
pipenv run pytest tests/unit/test_validators.py::TestPhoneNumberValidation::test_valid_phone_with_hyphens -v

# Run all tests in a class
pipenv run pytest tests/integration/test_conversation_handler.py::TestConversationHandler -v
```

### Coverage Reports

```bash
# Run tests with coverage
pipenv run pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Categories Explained

### Unit Tests (47 tests)

**File: `tests/unit/test_validators.py`**

Tests individual validation functions with comprehensive edge cases:

- **Phone Number Validation** (7 tests)
  - Valid formats: `010-1234-5678`, `011-123-4567`
  - Invalid formats: without hyphens, wrong prefix, too short, etc.

- **Date Validation** (9 tests)
  - Valid: future dates, today
  - Invalid: past dates, wrong format, invalid month/day, leap year edge cases

- **Time Validation** (11 tests)
  - Valid: `0000` to `2359`
  - Invalid: hour >= 24, minute >= 60, wrong length

- **Station Name Validation** (5 tests)
  - Valid: Korean station names (서울, 부산, etc.)
  - Invalid: too short, empty

- **Yes/No Validation** (5 tests)
  - Valid: Y/y, N/n
  - Invalid: other inputs

- **Choice Validation** (10 tests)
  - Train type choices: 1 (KTX), 2 (ALL)
  - Seat option choices: 1-4 (GENERAL_FIRST, GENERAL_ONLY, etc.)

### Integration Tests (61 tests)

#### Refactored App Tests (9 tests)
**File: `tests/integration/test_refactored_app.py`**

- Storage operations (user sessions, payment status, subscribers)
- Handler initialization
- Settings validation
- Message templates

#### Conversation Handler Tests (18 tests)
**File: `tests/integration/test_conversation_handler.py`**

Tests the complete multi-step conversation flow:

1. Start confirmation (Y/N)
2. Phone number input (with allow list check)
3. Password input (with Korail login)
4. Date input
5. Station inputs (source/destination)
6. Time inputs (departure/max departure)
7. Train type selection
8. Seat option selection
9. Passenger count input
10. Seat strategy selection (consecutive/random)
11. Final confirmation

**Edge Cases Covered:**
- Invalid input at each step
- Login failures and retries
- User not in allow list
- Already processing state

#### Reservation Service Tests (8 tests)
**File: `tests/integration/test_reservation_service.py`**

- Starting reservation processes
- Duplicate reservation prevention
- Cancelling reservations
- Cancelling all reservations (admin)
- Process cleanup on invalid PIDs
- Status checking

#### Payment Reminder Tests (11 tests)
**File: `tests/integration/test_payment_reminder.py`**

- Starting reminders
- Payment confirmation
- Reminder deactivation
- Timeout detection (10 minutes)
- Multiple concurrent reminders
- DateTime serialization through Redis
- Time-based tests using `freezegun`

#### Webhook Tests (15 tests)
**File: `tests/integration/test_webhook.py`**

- POST: Command routing (/start, /cancel, /status, etc.)
- POST: Payment confirmation messages
- POST: Admin authentication flow
- POST: Conversation message routing
- POST: Ignoring edited messages and chat member updates
- GET: Callback handling (success, failure, partial)
- GET: Multi-reservation callbacks
- Error handling for malformed requests

### E2E Tests (7 tests)

**File: `tests/e2e/test_full_reservation_flow.py`**

Complete user journeys from start to finish:

1. **Single Passenger Happy Path**: Complete 13-step flow
2. **Multi-Passenger Consecutive**: 3 passengers with consecutive seating
3. **Multi-Passenger Random**: 5 passengers with random allocation
4. **Cancellation Mid-Way**: User cancels during conversation
5. **Login Retry**: Failed login followed by successful retry
6. **Rejection at Start**: User says 'N' at initial confirmation
7. **Rejection at Final**: User says 'N' at final confirmation

Each test validates:
- Correct state transitions
- Data persistence through Redis
- Service interactions
- Message sending

## Key Testing Features

### 1. Redis Test Container

Tests use `testcontainers` to spin up a real Redis instance:

```python
# conftest.py automatically manages Redis lifecycle
def pytest_configure(config):
    # Starts Redis container before tests

def pytest_unconfigure(config):
    # Stops Redis container after tests
```

### 2. Mocking External Dependencies

Tests mock external services to avoid real API calls:

```python
@patch('services.korail_service.KorailService.login')
def test_password_input_success(self, mock_login):
    mock_login.return_value = True
    # Test logic here
```

Mocked services:
- Korail API (korail2 library)
- Telegram Bot API
- Background processes (subprocess.Popen)
- OS operations (os.kill)

### 3. Time Manipulation

Payment reminder tests use `freezegun` to control time:

```python
from freezegun import freeze_time

with freeze_time("2025-01-01 12:00:00"):
    # Tests run at this exact time
```

### 4. Fixtures

Common test fixtures in `conftest.py`:
- `redis_container`: Shared Redis container
- Automatic Redis cleanup between tests

## Test Coverage Goals

Current coverage focuses on:

✅ **Input Validation** - Comprehensive edge case testing
✅ **Conversation Flow** - All state transitions
✅ **Reservation Management** - Process lifecycle
✅ **Payment Reminders** - Timing and timeouts
✅ **Webhook Handling** - Request routing
✅ **E2E Flows** - Complete user journeys

## Running Tests in CI/CD

For continuous integration:

```bash
# Run tests with coverage and JUnit XML output
pipenv run pytest tests/ \
  --cov=src \
  --cov-report=xml \
  --cov-report=term \
  --junitxml=test-results.xml \
  -v
```

## Troubleshooting

### Tests Timeout

If tests timeout, check:
1. Redis container is starting properly
2. No infinite loops in code
3. Subprocess mocks are configured correctly

### Redis Connection Errors

```bash
# Ensure Docker is running
docker ps

# Check testcontainers logs
pytest tests/ -v --log-cli-level=DEBUG
```

### Import Errors

```bash
# Reinstall dependencies
pipenv install --dev

# Verify Python path
pipenv run python -c "import sys; print(sys.path)"
```

## Contributing New Tests

When adding new features, add corresponding tests:

1. **Unit Test**: For new validators or pure functions
   - Location: `tests/unit/`
   - Focus: Single function behavior

2. **Integration Test**: For new services or handlers
   - Location: `tests/integration/`
   - Focus: Service interactions

3. **E2E Test**: For new user flows
   - Location: `tests/e2e/`
   - Focus: Complete user journey

### Test Naming Convention

```python
def test_<feature>_<scenario>_<expected_result>():
    """Test description."""
    # Arrange
    # Act
    # Assert
```

### Example Test Template

```python
def test_new_feature_success(self):
    """Test new feature works correctly."""
    # Arrange - Setup test data
    chat_id = 12345

    # Act - Execute the feature
    result = self.service.new_feature(chat_id)

    # Assert - Verify results
    assert result is not None
    assert result.status == "success"
```

## Test Maintenance

### Regular Tasks

- [ ] Run full test suite before commits
- [ ] Update tests when changing business logic
- [ ] Add tests for bug fixes
- [ ] Keep coverage above 80%
- [ ] Review and remove obsolete tests

### Deprecated Tests Removed

The following outdated tests were removed during refactoring:

- ❌ `test_api.py` - Superficial endpoint checks
- ❌ `test_train_type_parsing.py` - Mock-based tests

Replaced with comprehensive integration tests that test real behavior.

## Quick Reference

```bash
# Fast feedback loop (unit tests only)
pipenv run pytest tests/unit/ -v

# Full test suite
pipenv run pytest tests/ -v

# With coverage
pipenv run pytest tests/ --cov=src --cov-report=term-missing

# Specific test pattern
pipenv run pytest tests/ -k "payment" -v

# Stop on first failure
pipenv run pytest tests/ -x

# Show print statements
pipenv run pytest tests/ -s

# Parallel execution (if installed pytest-xdist)
pipenv run pytest tests/ -n auto
```

## Support

For test-related issues:
1. Check this README
2. Review test file docstrings
3. Run with `--tb=short` for concise error output
4. Run with `--tb=long` for detailed traceback
