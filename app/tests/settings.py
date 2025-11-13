"""Settings overrides for tests"""

import logging
import os

# Set environment variables before importing settings
os.environ["PROTECTED_S3_CUSTOM_DOMAIN"] = "testserver/media"

# noinspection PyUnresolvedReferences
from config.settings import *  # noqa: F401, F403, E402, I251

SESSION_COOKIE_DOMAIN = ".testserver"
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN]
SECURE_SSL_REDIRECT = False
DEFAULT_SCHEME = "https"
COMPONENTS_REGISTRY_PREFIX = "localhost"
COMPONENTS_DOCKER_KEEP_CAPS_UNSAFE = True

TEMPLATES[0]["DIRS"].append(SITE_ROOT / "tests" / "templates")  # noqa 405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

FORUMS_MIN_ACCOUNT_AGE_DAYS = 0
ACCOUNT_RATE_LIMITS = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

ROOT_URLCONF = "tests.urls.root"

CELERY_BROKER = "memory"
CELERY_BROKER_URL = "memory://"

# Disable image resizing
PICTURES["PROCESSOR"] = "pictures.tasks.noop"  # noqa 405

# Disable debugging in tests
DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_LOGGING = False
COMPRESS_OFFLINE = False
COMPRESS_ENABLED = False

# Disable non-critical logging in tests
logging.disable(logging.CRITICAL)

# Ensure custom models for testing are found
INSTALLED_APPS += [  # noqa F405
    "tests.core_tests",
    "allauth.socialaccount.providers.dummy",
]

SOCIALACCOUNT_PROVIDERS.update({"dummy": {}})  # noqa F405
