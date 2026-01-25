"""
Test settings for EquipeMed project.
"""
from .settings import *

# Override settings for testing
DEBUG = True

# Use PostgreSQL for tests (same engine as development/production)
_DATABASE_NAME = os.getenv("DATABASE_NAME", "eqmd_dev")
_TEST_DATABASE_NAME = os.getenv("DATABASE_TEST_NAME", f"test_{_DATABASE_NAME}")

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DATABASE_ENGINE", "django.db.backends.postgresql"),
        "NAME": _DATABASE_NAME,
        "USER": os.getenv("DATABASE_USER", ""),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", ""),
        "PORT": os.getenv("DATABASE_PORT", ""),
        "TEST": {
            "NAME": _TEST_DATABASE_NAME,
        },
    }
}

# Disable CSRF for tests
CSRF_TRUSTED_ORIGINS = []

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Use simple password hasher for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Static files settings for tests
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files settings for tests
MEDIA_URL = '/media/'
MEDIA_ROOT = '/tmp/test_media'

# Cache settings for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Session settings for tests
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Celery settings for tests (if using Celery)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
