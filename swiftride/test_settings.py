"""
Test settings for SwiftRide.
Makes Celery run synchronously during tests (no Redis needed).
"""
from .settings import *

# Make Celery run synchronously during tests (no Redis needed)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use in-memory database for faster tests (optional)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': ':memory:',
#     }
# }

# Disable migrations during tests for faster execution (optional)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}

# Disable rate limiting in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': None,
        'user': None,
    },
}

# Override throttle classes for OTP views in tests
# Patch the OTP throttle rate to be unlimited in tests
# import sys
# if 'test' in sys.argv:
#     from rest_framework.throttling import BaseThrottle
    
#     class NoThrottle(BaseThrottle):
#         def allow_request(self, request, view):
#             return True
    
#     # Monkey patch the OTP throttle to be no-op in tests
#     import accounts.views
#     # Replace the throttle class used in the decorator
#     original_throttle = accounts.views.OTPRequestThrottle
#     accounts.views.OTPRequestThrottle = NoThrottle

