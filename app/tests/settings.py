"""Settings overrides for tests"""

import logging
import os

# Set environment variables before importing settings
os.environ["PROTECTED_S3_CUSTOM_DOMAIN"] = "testserver/media"

# noinspection PyUnresolvedReferences
from config.settings import *  # noqa: F401, F403, E402, I251

SESSION_COOKIE_DOMAIN = ".testserver"
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN, ".localhost"]
SECURE_SSL_REDIRECT = False

TEST_TEMPLATE_DIR = os.path.join(
    SITE_ROOT,  # noqa 405
    "tests/templates",
)
TEMPLATES[0]["DIRS"].append(TEST_TEMPLATE_DIR)  # noqa 405

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

ROOT_URLCONF = "tests.urls.root"
RENDERING_SUBDOMAIN_URL_CONF = "tests.urls.rendering_subdomain"
DEFAULT_SCHEME = "http"

DJANGO_LIVE_TEST_SERVER_ADDRESS = os.getenv("DJANGO_LIVE_TEST_SERVER_ADDRESS")

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
