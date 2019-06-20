# Django settings for comic project.
import glob
import os
import re
import traceback
import uuid
from datetime import timedelta
from distutils.util import strtobool as strtobool_i

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from raven.contrib.django.models import client
from rest_framework.response import Response

from config.denylist import USERNAME_DENYLIST
import environ

env = environ.Env()

def strtobool(val) -> bool:
    """ Returns disutils.util.strtobool as a boolean """
    return bool(strtobool_i(val))


# Default COMIC settings, to be included by settings.py
DEBUG = env.bool("DEBUG", default=True)
# DEBUG = False

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
APPS_DIR = os.path.join(SITE_ROOT, "comic")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_DB", "comic"),
        "USER": os.environ.get("POSTGRES_USER", "comic"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "secretpassword"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_USE_TLS = strtobool(os.environ.get("EMAIL_USE_TLS", "False"))
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "webmaster@localhost"
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "root@localhost")

ANONYMOUS_USER_NAME = "AnonymousUser"

AUTH_PROFILE_MODULE = "profiles.UserProfile"
LOGIN_URL = "/accounts/signin/"
LOGOUT_URL = "/accounts/signout/"

LOGIN_REDIRECT_URL = "/accounts/login-redirect/"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "UTC"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

# SITE_ID = int(os.environ.get("SITE_ID", "1"))

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", "/dbox/Dropbox/media/")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = "/media/"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = "/static/"

# Use memcached for caching
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "memcached:11211",
    }
}

ROOT_URLCONF = "config.urls"

DEFAULT_SCHEME = os.environ.get("DEFAULT_SCHEME", "https")

SESSION_COOKIE_DOMAIN = os.environ.get(
    "SESSION_COOKIE_DOMAIN", ".gc.localhost"
)
SESSION_COOKIE_SECURE = strtobool(
    os.environ.get("SESSION_COOKIE_SECURE", "False")
)
CSRF_COOKIE_SECURE = strtobool(os.environ.get("CSRF_COOKIE_SECURE", "False"))

# Set the allowed hosts to the cookie domain
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN, "web"]

# Security options
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = strtobool(
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False")
)
SECURE_CONTENT_TYPE_NOSNIFF = strtobool(
    os.environ.get("SECURE_CONTENT_TYPE_NOSNIFF", "False")
)
SECURE_BROWSER_XSS_FILTER = strtobool(
    os.environ.get("SECURE_BROWSER_XSS_FILTER", "False")
)
X_FRAME_OPTIONS = os.environ.get("X_FRAME_OPTIONS", "SAMEORIGIN")

# Serve files using django (debug only)
STATIC_URL = "/static/"

# List of finder classes that know how to find static files in
# various locations.
# STATICFILES_FINDERS = (
#     "django.contrib.staticfiles.finders.FileSystemFinder",
#     "django.contrib.staticfiles.finders.AppDirectoriesFinder",
#        # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
# )

# STATICFILES_STORAGE = (
#     "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
# )

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "d=%^l=xa02an9jn-$!*hy1)5yox$a-$2(ejt-2smimh=j4%8*b"
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR)],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                #"comic.core.contextprocessors.contextprocessors.comic_site",
                #"comic.core.contextprocessors.contextprocessors.google_analytics_id",
            ]
        },
    }
]

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    # Keep BrokenLinkEmailsMiddleware near the top
    "raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "comic.subdomains.middleware.subdomain_middleware",
    # "comic.subdomains.middleware.challenge_subdomain_middleware",
    # "comic.subdomains.middleware.subdomain_urlconf_middleware",
)


# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "config.wsgi.application"

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    # "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "raven.contrib.django.raven_compat",  # error logging
    "django_celery_results",  # database results backend
    "django_celery_beat",  # periodic tasks
    "djcelery_email",  # asynchronous emails
    # "userena",  # user profiles
    "guardian",  # userena dependency, per object permissions
    # "easy_thumbnails",  # userena dependency
    "social_django",  # social authentication with oauth2
    "rest_framework",  # provides REST API
    "rest_framework.authtoken",  # token auth for REST API
    # "crispy_forms",  # bootstrap forms
    # "favicon",  # favicon management
    # "django_select2",  # for multiple choice widgets
    # "django_summernote",  # for WYSIWYG page editing
    # "rest_framework_swagger",  # REST API Swagger spec
    "corsheaders",  # To manage CORS headers for frontend on different domain
    "django_extensions",
    "django_filters",
    "drf_yasg",
]

LOCAL_APPS = [
    # "comic.admins",
    "comic.api",
    # "comic.challenges",
    "comic.core",
    # "comic.evaluation",
    # "comic.jqfileupload",
    # "comic.pages",
    # "comic.participants",
    "comic.profiles",
    # "comic.teams",
    # "comic.uploads",
    # "comic.cases",
    # "comic.algorithms",
    # "comic.container_exec",
    # "comic.datasets",
    # "comic.submission_conversion",
    # "comic.statistics",
    "comic.eyra_benchmarks",
    "comic.eyra_algorithms",
    "comic.eyra_data",
    "comic.eyra_users",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = f'{os.environ.get("DJANGO_ADMIN_URL", "django-admin")}/'

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    # "userena.backends.UserenaAuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get(
    "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", ""
)
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get(
    "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", ""
)

# TODO: JM - Add the profile filling as a partial
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "comic.profiles.social_auth.pipeline.profile.create_profile",
    "comic.profiles.social_auth.pipeline.profile.add_to_default_group",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

# Do not sanitize redirects for social auth so we can redirect back to
# other subdomains
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

# Django 1.6 introduced a new test runner, use it
TEST_RUNNER = "django.test.runner.DiscoverRunner"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

# A sample logging configuration. More info in configuration can be found at
# https://docs.djangoproject.com/en/dev/topics/logging/ .
# This configuration writes WARNING and worse errors to an error log file, and
# sends an email to all admins. It also writes INFO logmessages and worse to a
# regular log file.
LOG_FILEPATH = "/tmp/django.log"
LOG_FILEPATH_ERROR = "/tmp/django_error.log"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "root": {"level": "WARNING", "handlers": ["sentry"]},
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "sentry": {
            "level": "ERROR",
            # To capture more than ERROR, change to WARNING, INFO, etc.
            "class": "raven.contrib.django.raven_compat.handlers.SentryHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "comic": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": True,
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "raven": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
        "sentry.errors": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

if strtobool(os.environ.get('SENTRY_DISABLE', 'False')):
    RAVEN_CONFIG = {"dsn" : ""}
else:
    RAVEN_CONFIG = {"dsn": os.environ.get("DJANGO_SENTRY_DSN", "")}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAdminUser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'EXCEPTION_HANDLER': 'comic.api.errors.custom_exception_handler'
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "django-db")
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_SOFT_TIME_LIMIT = 7200
CELERY_TASK_TIME_LIMIT = 7260

CELERY_BEAT_SCHEDULE = {
    "autoscale_gpu_node": {
        "task": "comic.eyra_benchmarks.tasks.autoscale_gpu_node",
        "schedule": timedelta(minutes=1),
    },
}

CELERY_TASK_ROUTES = {
    "comic.eyra_benchmarks.tasks.run_submission": "submission"
}

if MEDIA_ROOT[-1] != "/":
    msg = (
        "MEDIA_ROOT setting should end in a slash. Found '"
        + MEDIA_ROOT
        + "'. Please add a slash"
    )
    raise ImproperlyConfigured(msg)

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

    if ENABLE_DEBUG_TOOLBAR:
        INSTALLED_APPS += ("debug_toolbar",)

        MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

        DEBUG_TOOLBAR_CONFIG = {
            "SHOW_TOOLBAR_CALLBACK": "config.toolbar_callback"
        }

if strtobool(os.environ.get("WHITENOISE", "False")):
    MIDDLEWARE += ("whitenoise.middleware.WhiteNoiseMiddleware",)

CORS_ORIGIN_REGEX_WHITELIST = (
    r"^.*\.eyrabenchmark.net",
    r"https?://localhost:3000",
)

# CORS_ORIGIN_ALLOW_ALL = True
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = os.environ.get('S3_BUCKET', 'eyra-data01')
AWS_S3_REGION_NAME = os.environ.get('S3_REGION', 'eu-central-1')

PRIVATE_DOCKER_REGISTRY = os.environ.get("PRIVATE_DOCKER_REGISTRY", 'private-docker')
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", 'k8s-namespace')

# Set to True when running in the K8S cluster; for local development, set to False to use your local kubectl config.
K8S_USE_CLUSTER_CONFIG = True

AWS_AUTOSCALING_REGION=os.environ.get('AWS_AUTOSCALING_REGION', 'eu-central-1')
AWS_AUTOSCALING_ACCESS_KEY_ID=os.environ.get('AWS_AUTOSCALING_ACCESS_KEY_ID', '')
AWS_AUTOSCALING_SECRET_ACCESS_KEY=os.environ.get('AWS_AUTOSCALING_SECRET_ACCESS_KEY', '')