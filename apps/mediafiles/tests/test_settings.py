"""
Test-specific settings for the mediafiles app.
These settings override the main settings for testing purposes.
"""

import os
import tempfile
from pathlib import Path

# Test media settings
TEST_MEDIA_ROOT = tempfile.mkdtemp()
TEST_MEDIA_URL = '/test-media/'

# Security settings for testing
TEST_MEDIA_USE_UUID_FILENAMES = True
TEST_MEDIA_ENABLE_FILE_DEDUPLICATION = True
TEST_MEDIA_MAX_FILENAME_LENGTH = 100

# File size limits for testing (smaller than production)
TEST_MEDIA_IMAGE_MAX_SIZE = 1 * 1024 * 1024  # 1MB for testing
TEST_MEDIA_VIDEO_MAX_SIZE = 5 * 1024 * 1024  # 5MB for testing
TEST_MEDIA_VIDEO_MAX_DURATION = 30  # 30 seconds for testing

# Allowed file types for testing
TEST_MEDIA_ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
TEST_MEDIA_ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

# Allowed file extensions for testing
TEST_MEDIA_ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
TEST_MEDIA_ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']

# Test database settings (PostgreSQL)
TEST_DATABASES = {
    "default": {
        "ENGINE": os.getenv("DATABASE_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DATABASE_TEST_NAME", os.getenv("DATABASE_NAME", "eqmd_test")),
        "USER": os.getenv("DATABASE_USER", ""),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", ""),
        "PORT": os.getenv("DATABASE_PORT", ""),
    }
}

TEST_MIGRATION_MODULES = None

# Test logging configuration
TEST_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'mediafiles': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Password hashers for faster testing
TEST_PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend for testing
TEST_EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache configuration for testing
TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Static files for testing
TEST_STATIC_URL = '/static/'
TEST_STATIC_ROOT = tempfile.mkdtemp()

# Security settings for testing
TEST_SECRET_KEY = 'test-secret-key-for-mediafiles-testing-only'
TEST_DEBUG = True
TEST_ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Internationalization for testing
TEST_LANGUAGE_CODE = 'pt-br'
TEST_TIME_ZONE = 'America/Sao_Paulo'
TEST_USE_I18N = True
TEST_USE_TZ = True

# Test-specific middleware (minimal for faster testing)
TEST_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Test-specific installed apps
TEST_INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.hospitals',
    'apps.patients',
    'apps.events',
    'apps.mediafiles',
]

def get_test_settings():
    """
    Return a dictionary of test settings that can be used to override
    the main settings during testing.
    """
    return {
        'MEDIA_ROOT': TEST_MEDIA_ROOT,
        'MEDIA_URL': TEST_MEDIA_URL,
        'MEDIA_USE_UUID_FILENAMES': TEST_MEDIA_USE_UUID_FILENAMES,
        'MEDIA_ENABLE_FILE_DEDUPLICATION': TEST_MEDIA_ENABLE_FILE_DEDUPLICATION,
        'MEDIA_MAX_FILENAME_LENGTH': TEST_MEDIA_MAX_FILENAME_LENGTH,
        'MEDIA_IMAGE_MAX_SIZE': TEST_MEDIA_IMAGE_MAX_SIZE,
        'MEDIA_VIDEO_MAX_SIZE': TEST_MEDIA_VIDEO_MAX_SIZE,
        'MEDIA_VIDEO_MAX_DURATION': TEST_MEDIA_VIDEO_MAX_DURATION,
        'MEDIA_ALLOWED_IMAGE_TYPES': TEST_MEDIA_ALLOWED_IMAGE_TYPES,
        'MEDIA_ALLOWED_VIDEO_TYPES': TEST_MEDIA_ALLOWED_VIDEO_TYPES,
        'MEDIA_ALLOWED_IMAGE_EXTENSIONS': TEST_MEDIA_ALLOWED_IMAGE_EXTENSIONS,
        'MEDIA_ALLOWED_VIDEO_EXTENSIONS': TEST_MEDIA_ALLOWED_VIDEO_EXTENSIONS,
        'DATABASES': TEST_DATABASES,
        'LOGGING': TEST_LOGGING,
        'PASSWORD_HASHERS': TEST_PASSWORD_HASHERS,
        'EMAIL_BACKEND': TEST_EMAIL_BACKEND,
        'CACHES': TEST_CACHES,
        'STATIC_URL': TEST_STATIC_URL,
        'STATIC_ROOT': TEST_STATIC_ROOT,
        'SECRET_KEY': TEST_SECRET_KEY,
        'DEBUG': TEST_DEBUG,
        'ALLOWED_HOSTS': TEST_ALLOWED_HOSTS,
        'LANGUAGE_CODE': TEST_LANGUAGE_CODE,
        'TIME_ZONE': TEST_TIME_ZONE,
        'USE_I18N': TEST_USE_I18N,
        'USE_TZ': TEST_USE_TZ,
        'MIDDLEWARE': TEST_MIDDLEWARE,
        'INSTALLED_APPS': TEST_INSTALLED_APPS,
    }


def apply_test_settings(settings_module):
    """
    Apply test settings to a Django settings module.
    
    Usage:
        from apps.mediafiles.tests.test_settings import apply_test_settings
        apply_test_settings(settings)
    """
    test_settings = get_test_settings()
    
    for key, value in test_settings.items():
        setattr(settings_module, key, value)


# Test data helpers
def get_test_media_path():
    """Get the path to test media files"""
    return Path(__file__).parent / 'test_media'


def get_test_image_path(filename='small_image.jpg'):
    """Get the path to a test image file"""
    return get_test_media_path() / filename


def get_test_video_path(filename='test_video.mp4'):
    """Get the path to a test video file"""
    return get_test_media_path() / filename


def get_malicious_file_path(filename='malicious.jpg'):
    """Get the path to a malicious test file"""
    return get_test_media_path() / filename
