# SwiftRide Testing Guide

## 📋 How to Run Tests

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run All Tests
```bash
python manage.py test
```

### 3. Run Specific Test Suites
```bash
# Test accounts app
python manage.py test accounts

# Test rides app
python manage.py test rides

# Test payments app 
python manage.py test payments

# Test integration tests
python manage.py test rides.tests.test_integration
```

### 4. Run with Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 🧪 Test Coverage

### Existing Tests
- ✅ Unit tests for models
- ✅ API endpoint tests
- ✅ Permission tests
- ✅ Model property tests

### New Integration Tests
- ✅ Complete ride booking flow
- ✅ Payment processing
- ✅ Signal connections
- ✅ Ride cancellation flow

### Missing Tests (To Be Added)
- ⚠️ Notification delivery tests
- ⚠️ Chat integration tests
- ⚠️ Location tracking tests
- ⚠️ Safety features tests

---

## 🔍 Testing the Complete Ride Flow

### Manual Testing Steps

1. **Create User Account**
   ```bash
   POST /api/auth/send-otp/
   {
     "phone_number": "+2348011111111"
   }
   
   POST /api/auth/verify-otp/
   {
     "phone_number": "+2348011111111",
     "otp_code": "123456"
   }
   ```

2. **Register as Driver**
   ```bash
   POST /api/drivers/apply/
   {
     "vehicle_type": "sedan",
     "vehicle_color": "Black",
     "license_plate": "ABC123XY",
     "vehicle_year": 2020,
     "driver_license_number": "DL123456",
     "driver_license_expiry": "2025-12-31"
   }
   ```

3. **Admin Approves Driver**
   ```bash
   PATCH /api/drivers/admin/approve/{driver_id}/
   ```

4. **Driver Goes Online**
   ```bash
   POST /api/drivers/go-online/
   ```

5. **Rider Creates Ride**
   ```bash
   POST /api/rides/
   {
     "pickup_location": "Victoria Island, Lagos",
     "pickup_latitude": 6.4281,
     "pickup_longitude": 3.4219,
     "destination_location": "Lekki, Lagos",
     "destination_latitude": 6.4698,
     "destination_longitude": 3.5852,
     "ride_type": "immediate",
     "fare_amount": "1500.00"
   }
   ```

6. **Driver Accepts Ride**
   ```bash
   POST /api/rides/requests/{request_id}/accept/
   ```

7. **Driver Starts Ride**
   ```bash
   POST /api/rides/{ride_id}/start/
   ```

8. **Driver Completes Ride**
   ```bash
   POST /api/rides/{ride_id}/complete/
   ```

9. **Rider Rates Driver**
   ```bash
   POST /api/rides/{ride_id}/rate/
   {
     "rating": 5,
     "comment": "Great driver!"
   }
   ```

10. **Driver Rates Rider**
    ```bash
    POST /api/rides/{ride_id}/rate-rider/
    {
      "rating": 5,
      "comment": "Great passenger!"
    }
    ```

---

## 🔒 Security Testing

### Test Rate Limiting
```bash
# Try to create more than 10 rides per minute
for i in {1..15}; do
  curl -X POST /api/rides/ ...
done
# Should get 429 Too Many Requests after 10 requests
```

### Test Authentication
```bash
# Try to access protected endpoint without token
curl /api/rides/
# Should get 401 Unauthorized
```

### Test Authorization
```bash
# Try to access driver endpoint as rider
curl -X POST /api/rides/requests/{id}/accept/
# Should get 403 Forbidden
```

### Test Input Validation
```bash
# Try to create ride with invalid coordinates
POST /api/rides/
{
  "pickup_latitude": 200,  # Invalid (should be -90 to 90)
  "pickup_longitude": 300  # Invalid (should be -180 to 180)
}
# Should get 400 Bad Request
```

---

## 📊 Performance Testing

### Load Testing
```bash
# Install locust
pip install locust

# Create locustfile.py
# Run locust
locust -f locustfile.py

# Open browser to http://localhost:8089
```

### Database Query Testing
```bash
# Enable query logging
python manage.py shell
from django.db import connection
from django.conf import settings
settings.DEBUG = True

# Run test
# Check connection.queries
```

---

## 🐛 Debugging Tests

### Run Tests with Verbose Output
```bash
python manage.py test --verbosity=2
```

### Run Specific Test
```bash
python manage.py test rides.tests.test_integration.CompleteRideFlowIntegrationTest.test_complete_ride_flow
```

### Debug Failed Test
```bash
python manage.py test --pdb
```

### Check Test Database
```bash
python manage.py test --keepdb
```

---

## 📝 Writing New Tests

### Example Test Structure
```python
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

class MyTest(APITestCase):
    def setUp(self):
        # Set up test data
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)
    
    def test_my_feature(self):
        # Test your feature
        response = self.client.post('/api/endpoint/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['key'], 'expected_value')
```

---

## ✅ Test Checklist

### Before Deploying
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Security tests pass
- [ ] Performance tests pass
- [ ] Manual testing completed
- [ ] Code coverage > 80%
- [ ] No linter errors
- [ ] No security vulnerabilities

---

## 🚀 Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          python manage.py test
      - name: Run coverage
        run: |
          coverage run --source='.' manage.py test
          coverage report
```

---

*Last Updated: $(date)*

