"""
FILE LOCATION: swiftride/settings.py

✅ FIXED VERSION - Complete Django settings for SwiftRide
"""
import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '192.168.248.65,localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    # Django apps
    'jazzmin',  # Admin interface
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.gis',  # For location features (uncomment if using PostGIS)
    
    # Third-party apps
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',  # WebSocket support
    'django_filters', 
    'drf_yasg',  # API documentation
    'sslserver',
    'celery',
    
    # SwiftRide apps (in dependency order)
    'accounts',          # 1. Core - User model (foundation)
    'drivers',           # 2. Depends on: accounts
    'vehicles',          # 3. Depends on: drivers
    'pricing',           # 4. Independent
    'locations',         # 5. Independent
    'rides',             # 6. Depends on: accounts, drivers, vehicles, pricing, locations
    'payments',          # 7. Depends on: rides, accounts
    'notifications',     # 8. Supports all apps
    'chat',              # 9. Depends on: accounts
    'support',           # 10. Depends on: accounts
    'analytics',         # 11. Depends on: rides, drivers, payments
    'promotions',        # 12. Depends on: accounts, rides
    'safety',            # 13. Depends on: accounts, rides
    'admin_dashboard',   # 14. Depends on: all apps ⚠️ FIXED: was 'admin_dashboard_app'
]  
 
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'swiftride.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'swiftride.wsgi.application'
ASGI_APPLICATION = 'swiftride.asgi.application'

# ========================================
# DATABASE
# ========================================
# Development: SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Production: PostgreSQL (uncomment and configure)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.contrib.gis.db.backends.postgis',  # or django.db.backends.postgresql
#         'NAME': os.getenv('DB_NAME', 'swiftride_db'),
#         'USER': os.getenv('DB_USER', 'swiftride_user'),
#         'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
#         'HOST': os.getenv('DB_HOST', 'localhost'),
#         'PORT': os.getenv('DB_PORT', '5432'),
#         'ATOMIC_REQUESTS': True,
#         'CONN_MAX_AGE': 600,
#     }
# }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========================================
# REST FRAMEWORK
# ========================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
}

# ========================================
# JWT SETTINGS
# ========================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ========================================
# CORS SETTINGS
# ========================================
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000'
).split(',')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ========================================
# CHANNELS (WebSocket)
# ========================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(
                os.getenv('REDIS_HOST', 'localhost'),
                int(os.getenv('REDIS_PORT', 6379))
            )],
        },
    },
}

# ========================================
# CELERY
# ========================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# ========================================
# CACHE
# ========================================
# Development: Local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Production: Redis cache (uncomment)
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# ========================================
# SESSION SETTINGS (⚠️ FIXED: Removed duplicate)
# ========================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database sessions
SESSION_COOKIE_AGE = 86400 * 30  # 30 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # True in production

# ========================================
# FIREBASE CLOUD MESSAGING
# ========================================
FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY', '')

# ========================================
# SMS PROVIDERS
# ========================================
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'console')  # africastalking, twilio, termii, console

# Africa's Talking
AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY', '')

# Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Termii
TERMII_API_KEY = os.getenv('TERMII_API_KEY', '')
TERMII_SENDER_ID = os.getenv('TERMII_SENDER_ID', 'SwiftRide')

# ========================================
# EMAIL SETTINGS
# ========================================
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'SwiftRide <noreply@swiftride.com>')

# ========================================
# PAYMENT GATEWAYS
# ========================================
# Paystack
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')

# Flutterwave
FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv('FLUTTERWAVE_ENCRYPTION_KEY', '')

# Stripe
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')

# ========================================
# GOOGLE MAPS API
# ========================================
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

# ========================================
# RIDE SETTINGS
# ========================================
RIDE_SETTINGS = {
    'BASE_FARE': float(os.getenv('BASE_FARE', 500)),  # ₦500
    'PRICE_PER_KM': float(os.getenv('PRICE_PER_KM', 150)),  # ₦150/km
    'PRICE_PER_MINUTE': float(os.getenv('PRICE_PER_MINUTE', 15)),  # ₦15/min
    'MINIMUM_FARE': float(os.getenv('MINIMUM_FARE', 800)),  # ₦800
    'CANCELLATION_FEE': float(os.getenv('CANCELLATION_FEE', 200)),  # ₦200
    'PLATFORM_FEE_PERCENTAGE': float(os.getenv('PLATFORM_FEE', 15)),  # 15%
    'MAX_SEARCH_RADIUS_KM': float(os.getenv('MAX_SEARCH_RADIUS', 5)),  # 5km
    'DRIVER_TIMEOUT_SECONDS': int(os.getenv('DRIVER_TIMEOUT', 30)),  # 30s
}

# ========================================
# DRIVER SETTINGS
# ========================================
DRIVER_SETTINGS = {
    'MIN_RATING': float(os.getenv('MIN_DRIVER_RATING', 3.5)),
    'MAX_REJECTION_RATE': float(os.getenv('MAX_REJECTION_RATE', 30)),  # 30%
    'BACKGROUND_CHECK_REQUIRED': True,
}

# ========================================
# FILE UPLOAD SETTINGS
# ========================================
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'image/jpeg', 'image/png']

# ========================================
# LOGGING
# ========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'swiftride.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'swiftride': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ========================================
# ADMIN CUSTOMIZATION
# ========================================
ADMIN_SITE_HEADER = 'SwiftRide Admin'
ADMIN_SITE_TITLE = 'SwiftRide Admin Portal'
ADMIN_INDEX_TITLE = 'Welcome to SwiftRide Administration'

# ========================================
# SECURITY SETTINGS (Production)
# ========================================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'