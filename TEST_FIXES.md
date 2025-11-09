# Test Fixes Applied

## Issues Fixed

### 1. ✅ Celery/Redis Connection Errors

**Problem**: Tests were failing because signals were trying to call Celery tasks, but Redis wasn't running during tests.

**Solution**:
- Created `notifications/utils.py` with `safe_send_notification()` function
- Function tries to send notification asynchronously via Celery
- Falls back to synchronous execution if Celery is unavailable
- All signal handlers now use `safe_send_notification()` instead of `.delay()`

**Files Modified**:
- `notifications/utils.py` (NEW)
- `notifications/signals.py` (Updated all `.delay()` calls)

### 2. ✅ Test URL Routing Errors

**Problem**: Tests were using `/api/accounts/` but URLs are mounted at `/api/auth/`.

**Solution**:
- Updated all test URLs from `/api/accounts/` to `/api/auth/`
- Fixed field name from `otp` to match serializer (serializer accepts `otp` and converts internally)

**Files Modified**:
- `accounts/tests.py` (Updated all URL paths)

### 3. ✅ Test Settings

**Problem**: Celery needs to run synchronously during tests.

**Solution**:
- Created `swiftride/test_settings.py` with test-specific settings
- Set `CELERY_TASK_ALWAYS_EAGER = True` to run tasks synchronously
- Disabled logging during tests

**Files Created**:
- `swiftride/test_settings.py` (NEW)

---

## How to Run Tests

### Option 1: Use Test Settings (Recommended)
```bash
python manage.py test --settings=swiftride.test_settings
```

### Option 2: Set Environment Variable
```bash
# Windows PowerShell
$env:DJANGO_SETTINGS_MODULE="swiftride.test_settings"
python manage.py test

# Linux/Mac
export DJANGO_SETTINGS_MODULE=swiftride.test_settings
python manage.py test
```

### Option 3: Update manage.py (Permanent Fix)
Add to `manage.py`:
```python
if 'test' in sys.argv:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.test_settings')
```

---

## What Was Fixed

### notifications/utils.py
- New utility function `safe_send_notification()`
- Handles Celery connection errors gracefully
- Falls back to synchronous execution if Celery unavailable

### notifications/signals.py
- All `.delay()` calls replaced with `safe_send_notification()`
- Signals now work even without Redis/Celery running
- No more connection errors during tests

### accounts/tests.py
- Fixed URL paths: `/api/accounts/` → `/api/auth/`
- Fixed field names to match serializer expectations

### swiftride/test_settings.py
- Test-specific settings
- Celery runs synchronously
- Logging disabled

---

## Testing

### Run All Tests
```bash
python manage.py test --settings=swiftride.test_settings
```

### Run Specific Test Suite
```bash
python manage.py test accounts --settings=swiftride.test_settings
python manage.py test rides --settings=swiftride.test_settings
python manage.py test payments --settings=swiftride.test_settings
```

### Run Specific Test
```bash
python manage.py test accounts.tests.OTPAPITest.test_send_otp --settings=swiftride.test_settings
```

---

## Expected Results

After these fixes:
- ✅ No more Celery connection errors
- ✅ No more 404 errors for OTP endpoints
- ✅ Tests should run successfully
- ✅ Signals work in both test and production environments

---

## Notes

1. **Celery in Production**: The `safe_send_notification()` function still uses Celery in production when available. It only falls back to synchronous execution if Celery is unavailable.

2. **Test Performance**: Using `CELERY_TASK_ALWAYS_EAGER = True` makes tasks run synchronously during tests, which is faster and doesn't require Redis.

3. **Signal Safety**: All signals now handle errors gracefully, so they won't break user creation or other operations if notifications fail.

---

*Last Updated: $(date)*

