import logging
import os

# Set environment variables before importing settings
os.environ["PROTECTED_S3_CUSTOM_DOMAIN"] = "testserver/media"

# noinspection PyUnresolvedReferences
from config.settings import *  # noqa: F401, F403

""" Settings overrides for tests """

ALLOWED_HOSTS = [".testserver"]

WHITENOISE_AUTOREFRESH = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_BROKER = "memory"
CELERY_BROKER_URL = "memory://"

# Disable debugging in tests
DEBUG = False
TEMPLATE_DEBUG = False
DEBUG_LOGGING = False

# Disable non-critical logging in tests
logging.disable(logging.CRITICAL)
