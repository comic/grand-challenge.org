import os

# Set environment variables before importing settings
os.environ["PROTECTED_S3_CUSTOM_DOMAIN"] = "testserver/media"

# noinspection PyUnresolvedReferences
from config.settings import *

""" Settings overrides for tests """

ALLOWED_HOSTS = [".testserver"]
WHITENOISE_AUTOREFRESH = True
