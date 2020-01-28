import os
import re
from datetime import timedelta
from distutils.util import strtobool as strtobool_i

import sentry_sdk
from corsheaders.defaults import default_headers
from django.contrib.messages import constants as messages
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from config.denylist import USERNAME_DENYLIST


def strtobool(val) -> bool:
    """Return disutils.util.strtobool as a boolean."""
    return bool(strtobool_i(val))


DEBUG = strtobool(os.environ.get("DEBUG", "True"))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Who gets the 404 notifications?
manager_email = os.environ.get("MANAGER_EMAIL", None)
if manager_email:
    MANAGERS = [("Manager", manager_email)]

IGNORABLE_404_URLS = [
    re.compile(r".*\.(php|cgi|asp).*"),
    re.compile(r"^/phpmyadmin.*"),
    re.compile(r"^/gen204.*"),
    re.compile(r"^/wp-content.*"),
    re.compile(r".*/trackback.*"),
    re.compile(r"^/site/.*"),
    re.compile(r"^/media/cache/.*"),
]

# Used as starting points for various other paths. realpath(__file__) starts in
# the config dir. We need to  go one dir higher so path.join("..")
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
APPS_DIR = os.path.join(SITE_ROOT, "grandchallenge")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_DB", "grandchallenge"),
        "USER": os.environ.get("POSTGRES_USER", "grandchallenge"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "secretpassword"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": "",
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
USERENA_USE_HTTPS = False
USERENA_DEFAULT_PRIVACY = "open"
LOGIN_URL = "/accounts/signin/"
LOGOUT_URL = "/accounts/signout/"

LOGIN_REDIRECT_URL = "/accounts/login-redirect/"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL

# Do not give message popups saying "you have been logged out". Users are expected
# to know they have been logged out when they click the logout button
USERENA_USE_MESSAGES = (False,)

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

SITE_ID = int(os.environ.get("SITE_ID", "1"))

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

##############################################################################
#
# Storage
#
##############################################################################
DEFAULT_FILE_STORAGE = "grandchallenge.core.storage.PublicS3Storage"

# Subdirectories on root for various files
JQFILEUPLOAD_UPLOAD_SUBIDRECTORY = "jqfileupload"
IMAGE_FILES_SUBDIRECTORY = "images"
EVALUATION_FILES_SUBDIRECTORY = "evaluation"

# This is for storing files that should not be served to the public
PRIVATE_S3_STORAGE_KWARGS = {
    "access_key": os.environ.get("PRIVATE_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PRIVATE_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PRIVATE_S3_STORAGE_BUCKET_NAME", "grand-challenge-private"
    ),
    "auto_create_bucket": True,
    "endpoint_url": os.environ.get(
        "PRIVATE_S3_STORAGE_ENDPOINT_URL", "http://minio-private:9000"
    ),
    # Do not overwrite files, we get problems with jqfileupload otherwise
    "file_overwrite": False,
    "default_acl": "private",
}
PROTECTED_S3_STORAGE_KWARGS = {
    "access_key": os.environ.get("PROTECTED_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PROTECTED_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PROTECTED_S3_STORAGE_BUCKET_NAME", "grand-challenge-protected"
    ),
    "auto_create_bucket": True,
    "endpoint_url": os.environ.get(
        "PROTECTED_S3_STORAGE_ENDPOINT_URL", "http://minio-protected:9000"
    ),
    # This is the domain where people will be able to go to download data
    # from this bucket. Usually we would use reverse to find this out,
    # but this needs to be defined before the database is populated
    "custom_domain": os.environ.get(
        "PROTECTED_S3_CUSTOM_DOMAIN", "gc.localhost/media"
    ),
    "file_overwrite": False,
    "default_acl": "private",
}
PUBLIC_S3_STORAGE_KWARGS = {
    "access_key": os.environ.get("PUBLIC_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PUBLIC_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PUBLIC_S3_STORAGE_BUCKET_NAME", "grand-challenge-public"
    ),
    "file_overwrite": False,
    # Public bucket so do not use querystring_auth
    "querystring_auth": False,
    "default_acl": "public-read",
}

##############################################################################
#
# Caching
#
##############################################################################

CACHES = {
    "default": {
        "BACKEND": "speedinfo.backends.proxy_cache",
        "CACHE_BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "memcached:11211",
    }
}
SPEEDINFO_STORAGE = "speedinfo.storage.cache.storage.CacheStorage"

ROOT_URLCONF = "config.urls"
SUBDOMAIN_URL_CONF = "grandchallenge.subdomains.urls"
DEFAULT_SCHEME = os.environ.get("DEFAULT_SCHEME", "https")

SESSION_COOKIE_DOMAIN = os.environ.get(
    "SESSION_COOKIE_DOMAIN", ".gc.localhost"
)
# We're always running behind a proxy so set these to true
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = "/static/"

STATIC_HOST = os.environ.get("DJANGO_STATIC_HOST", "")
STATIC_URL = f"{STATIC_HOST}/static/"

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

# Vendored static files will be put here
STATICFILES_DIRS = ["/opt/static/"]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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
                "grandchallenge.core.context_processors.challenge",
                "grandchallenge.core.context_processors.google_keys",
                "grandchallenge.core.context_processors.debug",
                "grandchallenge.core.context_processors.sentry_dsn",
                "grandchallenge.core.context_processors.policy_pages",
            ]
        },
    }
]

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",  # Keep security at top
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Keep whitenoise after security and before all else
    "corsheaders.middleware.CorsMiddleware",  # Keep CORS near the top
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    # Keep BrokenLinkEmailsMiddleware near the top
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # subdomain_middleware after CurrentSiteMiddleware
    "grandchallenge.subdomains.middleware.subdomain_middleware",
    "grandchallenge.subdomains.middleware.challenge_subdomain_middleware",
    "grandchallenge.subdomains.middleware.subdomain_urlconf_middleware",
    # Flatpage fallback almost last
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    # speedinfo at the end but before FetchFromCacheMiddleware
    "speedinfo.middleware.ProfilerMiddleware",
)

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "config.wsgi.application"

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",  # Keep whitenoise above staticfiles
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.postgres",
    "django.contrib.flatpages",
]

THIRD_PARTY_APPS = [
    "django_celery_results",  # database results backend
    "django_celery_beat",  # periodic tasks
    "djcelery_email",  # asynchronous emails
    "userena",  # user profiles
    "guardian",  # userena dependency, per object permissions
    "easy_thumbnails",  # userena dependency
    "social_django",  # social authentication with oauth2
    "rest_framework",  # provides REST API
    "rest_framework.authtoken",  # token auth for REST API
    "crispy_forms",  # bootstrap forms
    "favicon",  # favicon management
    "django_select2",  # for multiple choice widgets
    "django_summernote",  # for WYSIWYG page editing
    "dal",  # for autocompletion of selection fields
    "dal_select2",  # for autocompletion of selection fields
    "django_extensions",  # custom extensions
    "simple_history",  # for object history
    "corsheaders",  # to allow api communication from subdomains
    "speedinfo",  # for profiling views
    "drf_yasg",
]

LOCAL_APPS = [
    "grandchallenge.admins",
    "grandchallenge.api",
    "grandchallenge.challenges",
    "grandchallenge.core",
    "grandchallenge.evaluation",
    "grandchallenge.jqfileupload",
    "grandchallenge.pages",
    "grandchallenge.participants",
    "grandchallenge.profiles",
    "grandchallenge.teams",
    "grandchallenge.uploads",
    "grandchallenge.cases",
    "grandchallenge.algorithms",
    "grandchallenge.container_exec",
    "grandchallenge.datasets",
    "grandchallenge.submission_conversion",
    "grandchallenge.statistics",
    "grandchallenge.archives",
    "grandchallenge.patients",
    "grandchallenge.studies",
    "grandchallenge.registrations",
    "grandchallenge.annotations",
    "grandchallenge.retina_core",
    "grandchallenge.retina_importers",
    "grandchallenge.retina_api",
    "grandchallenge.worklists",
    "grandchallenge.workstations",
    "grandchallenge.reader_studies",
    "grandchallenge.workstation_configs",
    "grandchallenge.policies",
    "grandchallenge.favicons",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = f'{os.environ.get("DJANGO_ADMIN_URL", "django-admin")}/'

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "userena.backends.UserenaAuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "GA_TRACKING_ID")

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
    "grandchallenge.profiles.social_auth.pipeline.profile.create_profile",
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

# WYSIWYG editing with Summernote
SUMMERNOTE_THEME = "bs4"
SUMMERNOTE_CONFIG = {
    "attachment_model": "uploads.SummernoteAttachment",
    "attachment_require_authentication": True,
    "summernote": {
        "width": "100%",
        "toolbar": [
            ["style", ["style"]],
            [
                "font",
                ["bold", "italic", "underline", "strikethrough", "clear"],
            ],
            ["para", ["ul", "ol", "paragraph"]],
            ["insert", ["link", "picture", "hr"]],
            ["view", ["fullscreen", "codeview"]],
            ["help", ["help"]],
        ],
    },
}

# Settings for allowed HTML
BLEACH_ALLOWED_TAGS = [
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "col",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strike",
    "strong",
    "table",
    "tbody",
    "thead",
    "td",
    "th",
    "tr",
    "u",
    "ul",
]
BLEACH_ALLOWED_ATTRIBUTES = {
    "*": ["class", "data-toggle", "id", "style", "role"],
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],
    "img": ["height", "src", "width"],
    # For bootstrap tables: https://getbootstrap.com/docs/4.3/content/tables/
    "th": ["scope", "colspan"],
    "td": ["colspan"],
}
BLEACH_ALLOWED_STYLES = ["height", "margin-left", "text-align", "width"]
BLEACH_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
BLEACH_STRIP = strtobool(os.environ.get("BLEACH_STRIP", "True"))

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
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler"}
    },
    "loggers": {
        "grandchallenge": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": True,
        },
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "werkzeug": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

SENTRY_DSN = os.environ.get("DJANGO_SENTRY_DSN", "")
SENTRY_ENABLE_JS_REPORTING = strtobool(
    os.environ.get("SENTRY_ENABLE_JS_REPORTING", "False")
)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
        RedisIntegration(),
    ],
)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAdminUser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "grandchallenge.api.pagination.MaxLimit1000OffsetPagination",
    "PAGE_SIZE": 100,
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    }
}

VALID_SUBDOMAIN_REGEX = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
CORS_ORIGIN_REGEX_WHITELIST = [
    rf"^https:\/\/{VALID_SUBDOMAIN_REGEX}{re.escape(SESSION_COOKIE_DOMAIN)}$"
]
CORS_ALLOW_HEADERS = [
    *default_headers,
    "content-range",
    "content-disposition",
    "content-description",
]

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "django-db")
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_SOFT_TIME_LIMIT = int(
    os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "7200")
)
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "7260"))

CONTAINER_EXEC_DOCKER_BASE_URL = os.environ.get(
    "CONTAINER_EXEC_DOCKER_BASE_URL", "unix://var/run/docker.sock"
)
CONTAINER_EXEC_DOCKER_TLSVERIFY = strtobool(
    os.environ.get("CONTAINER_EXEC_DOCKER_TLSVERIFY", "False")
)
CONTAINER_EXEC_DOCKER_TLSCACERT = os.environ.get(
    "CONTAINER_EXEC_DOCKER_TLSCACERT", ""
)
CONTAINER_EXEC_DOCKER_TLSCERT = os.environ.get(
    "CONTAINER_EXEC_DOCKER_TLSCERT", ""
)
CONTAINER_EXEC_DOCKER_TLSKEY = os.environ.get(
    "CONTAINER_EXEC_DOCKER_TLSKEY", ""
)
CONTAINER_EXEC_MEMORY_LIMIT = os.environ.get(
    "CONTAINER_EXEC_MEMORY_LIMIT", "4g"
)
CONTAINER_EXEC_IO_IMAGE = "alpine:3.9"
CONTAINER_EXEC_IO_SHA256 = (
    "sha256:055936d3920576da37aa9bc460d70c5f212028bda1c08c0879aedf03d7a66ea1"
)
CONTAINER_EXEC_CPU_QUOTA = int(
    os.environ.get("CONTAINER_EXEC_CPU_QUOTA", "100000")
)
CONTAINER_EXEC_CPU_PERIOD = int(
    os.environ.get("CONTAINER_EXEC_CPU_PERIOD", "100000")
)
CONTAINER_EXEC_PIDS_LIMIT = int(
    os.environ.get("CONTAINER_EXEC_PIDS_LIMIT", "128")
)
CONTAINER_EXEC_CPU_SHARES = int(
    os.environ.get("CONTAINER_EXEC_CPU_SHARES", "1024")  # Default weight
)
CONTAINER_EXEC_DOCKER_RUNTIME = os.environ.get(
    "CONTAINER_EXEC_DOCKER_RUNTIME", None
)

CELERY_BEAT_SCHEDULE = {
    "cleanup_stale_uploads": {
        "task": "grandchallenge.jqfileupload.tasks.cleanup_stale_uploads",
        "schedule": timedelta(hours=1),
    },
    "clear_sessions": {
        "task": "grandchallenge.core.tasks.clear_sessions",
        "schedule": timedelta(days=1),
    },
    "update_filter_classes": {
        "task": "grandchallenge.challenges.tasks.update_filter_classes",
        "schedule": timedelta(minutes=5),
    },
    "validate_external_challenges": {
        "task": "grandchallenge.challenges.tasks.check_external_challenge_urls",
        "schedule": timedelta(days=1),
    },
    "stop_expired_services": {
        "task": "grandchallenge.container_exec.tasks.stop_expired_services",
        "kwargs": {"app_label": "workstations", "model_name": "session"},
        "schedule": timedelta(minutes=5),
    },
    # Cleanup evaluation jobs on the evaluation queue
    "mark_long_running_evaluation_jobs_failed": {
        "task": "grandchallenge.container_exec.tasks.mark_long_running_jobs_failed",
        "kwargs": {"app_label": "evaluation", "model_name": "job"},
        "options": {"queue": "evaluation"},
        "schedule": timedelta(hours=1),
    },
}

CELERY_TASK_ROUTES = {
    "grandchallenge.container_exec.tasks.execute_job": "evaluation",
    "grandchallenge.container_exec.tasks.start_service": "workstations",
    "grandchallenge.container_exec.tasks.stop_service": "workstations",
    "grandchallenge.container_exec.tasks.stop_expired_services": "workstations",
    "grandchallenge.cases.tasks.build_images": "images",
}

# Set which template pack to use for forms
CRISPY_TEMPLATE_PACK = "bootstrap4"

# When using bootstrap error messages need to be renamed to danger
MESSAGE_TAGS = {messages.ERROR: "danger"}

# The name of the group whose members will be able to create reader studies
READER_STUDY_CREATORS_GROUP_NAME = "reader_study_creators"

# The workstation that is accessible by all authorised users
DEFAULT_WORKSTATION_SLUG = os.environ.get(
    "DEFAULT_WORKSTATION_SLUG", "cirrus-core"
)
WORKSTATIONS_BASE_IMAGE_QUERY_PARAM = "image"
WORKSTATIONS_OVERLAY_QUERY_PARAM = "overlay"
WORKSTATIONS_READY_STUDY_QUERY_PARAM = "readerStudy"
WORKSTATIONS_CONFIG_QUERY_PARAM = "config"
# The name of the network that the workstations will be attached to
WORKSTATIONS_NETWORK_NAME = os.environ.get(
    "WORKSTATIONS_NETWORK_NAME", "grand-challengeorg_workstations"
)
# The total limit on the number of sessions
WORKSTATIONS_MAXIMUM_SESSIONS = int(
    os.environ.get("WORKSTATIONS_MAXIMUM_SESSIONS", "10")
)
# The name of the group whose members will be able to create workstations
WORKSTATIONS_CREATORS_GROUP_NAME = "workstation_creators"
WORKSTATIONS_SESSION_DURATION_LIMIT = int(
    os.environ.get("WORKSTATIONS_SESSION_DURATION_LIMIT", "10000")
)

# The name of the group whose members will be able to create algorithms
ALGORITHMS_CREATORS_GROUP_NAME = "algorithm_creators"

# Disallow some challenge names due to subdomain or media folder clashes
DISALLOWED_CHALLENGE_NAMES = [
    "m",
    IMAGE_FILES_SUBDIRECTORY,
    "logos",
    "banners",
    "mugshots",
    "docker",
    EVALUATION_FILES_SUBDIRECTORY,
    "evaluation-supplementary",
    "favicon",
    "i",
    "cache",
    JQFILEUPLOAD_UPLOAD_SUBIDRECTORY,
    *USERNAME_DENYLIST,
]

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

    # Allow localhost in development
    CORS_ORIGIN_REGEX_WHITELIST += [r"^http://localhost:8888$"]

    LOGGING["loggers"]["grandchallenge"]["level"] = "DEBUG"

    PUBLIC_S3_STORAGE_KWARGS.update(
        {
            "custom_domain": f"localhost:9000/{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}",
            "auto_create_bucket": True,
            "secure_urls": False,
            "endpoint_url": "http://minio-public:9000",
        }
    )

    if ENABLE_DEBUG_TOOLBAR:
        INSTALLED_APPS += ("debug_toolbar",)

        MIDDLEWARE = (
            "debug_toolbar.middleware.DebugToolbarMiddleware",
            *MIDDLEWARE,
        )

        DEBUG_TOOLBAR_CONFIG = {
            "SHOW_TOOLBAR_CALLBACK": "config.toolbar_callback"
        }

# Modality name constants
MODALITY_OCT = "OCT"  # Optical coherence tomography
MODALITY_CF = "Fundus Photography"  # Color fundus photography
MODALITY_FA = "Flurescein Angiography"  # Fluorescein angiography
MODALITY_IR = "Infrared Reflectance Imaging"  # Infrared Reflectance imaging

# Maximum file size in bytes to be opened by SimpleITK.ReadImage in cases.models.Image.get_sitk_image()
MAX_SITK_FILE_SIZE = 268435456  # == 256 mb

# Tile size in pixels to be used when creating dzi for tif files
DZI_TILE_SIZE = 2560

# Default maximum width or height for thumbnails in retina workstation
RETINA_DEFAULT_THUMBNAIL_SIZE = 128

# Retina specific settings
RETINA_IMAGE_CACHE_TIME = 60 * 60 * 24 * 7
RETINA_GRADERS_GROUP_NAME = "retina_graders"
RETINA_ADMINS_GROUP_NAME = "retina_admins"
RETINA_IMPORT_USER_NAME = "retina_import_user"
RETINA_EXCEPTION_ARCHIVE = "Australia"
