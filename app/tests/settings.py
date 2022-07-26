"""Settings overrides for tests"""

import logging
import os

# Set environment variables before importing settings
os.environ["PROTECTED_S3_CUSTOM_DOMAIN"] = "testserver/media"

# noinspection PyUnresolvedReferences
from config.settings import *  # noqa: F401, F403, E402

SESSION_COOKIE_DOMAIN = ".testserver"
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN]
SECURE_SSL_REDIRECT = False

# Speed up token generation in tests
REST_KNOX[  # noqa F405
    "SECURE_HASH_ALGORITHM"
] = "cryptography.hazmat.primitives.hashes.MD5"

WHITENOISE_AUTOREFRESH = True
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

FORUMS_MIN_ACCOUNT_AGE_DAYS = 0
ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN = 0
ACCOUNT_RATE_LIMITS = {}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_BROKER = "memory"
CELERY_BROKER_URL = "memory://"

# Disable image resizing
STDIMAGE_LOGO_VARIATIONS = {"x20": (None,)}
STDIMAGE_SOCIAL_VARIATIONS = {"x20": (None,)}
STDIMAGE_BANNER_VARIATIONS = {}

# Disable debugging in tests
DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_LOGGING = False

# Disable non-critical logging in tests
logging.disable(logging.CRITICAL)
