import json
import os
import re
import socket
from datetime import timedelta
from itertools import product
from pathlib import Path
from subprocess import CalledProcessError

import sentry_sdk
from celery.schedules import crontab
from corsheaders.defaults import default_headers
from csp import constants as csp_constants
from disposable_email_domains import blocklist
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django.utils._os import safe_join
from django.utils.timezone import now
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from config.denylist import USERNAME_DENYLIST
from grandchallenge.components.exceptions import PriorStepFailed
from grandchallenge.core.utils import strtobool
from grandchallenge.core.utils.markdown import BS4Extension

MEGABYTE = 1024 * 1024
GIGABYTE = 1024 * MEGABYTE
TERABYTE = 1024 * GIGABYTE

DEBUG = strtobool(os.environ.get("DEBUG", "False"))

COMMIT_ID = os.environ.get("COMMIT_ID", "unknown")

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
    re.compile(r"^/wp.*"),
    re.compile(r"^/wordpress/.*"),
    re.compile(r"^/old/.*", flags=re.IGNORECASE),
    re.compile(r".*/trackback.*"),
    re.compile(r"^/site/.*"),
    re.compile(r"^/media/cache/.*"),
    re.compile(r"^/favicon.ico$"),
]

# Used as starting points for various other paths. realpath(__file__) starts in
# the config dir. We need to  go one dir higher so path.join("..")
SITE_ROOT = Path(__file__).resolve(strict=True).parent.parent

if strtobool(os.environ.get("POSTGRES_USE_RDS_PROXY", "false")):
    # From https://www.amazontrust.com/repository/
    # See https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.howitworks.html#rds-proxy-security
    ssl_root_cert = "amazon-root-ca.pem"
else:
    ssl_root_cert = "global-bundle.pem"

DATABASES = {
    "default": {
        "ENGINE": "grandchallenge.core.db.postgres_iam",
        "NAME": os.environ.get("POSTGRES_DB", "grandchallenge"),
        "USER": os.environ.get("POSTGRES_USER", "grandchallenge"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "secretpassword"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "use_iam_auth": strtobool(
                os.environ.get("POSTGRES_USE_IAM_AUTH", "false")
            ),
            "sslmode": os.environ.get("POSTGRES_SSL_MODE", "prefer"),
            "sslrootcert": os.path.join(
                SITE_ROOT, "config", "certs", ssl_root_cert
            ),
        },
        "ATOMIC_REQUESTS": strtobool(
            os.environ.get("ATOMIC_REQUESTS", "True")
        ),
        "CONN_MAX_AGE": int(os.environ.get("CONN_MAX_AGE", "0")),
        "CONN_HEALTH_CHECKS": strtobool(
            os.environ.get("CONN_HEALTH_CHECKS", "false")
        ),
        "DISABLE_SERVER_SIDE_CURSORS": strtobool(
            os.environ.get("DISABLE_SERVER_SIDE_CURSORS", "false")
        ),
    }
}

EMAIL_BACKEND = "grandchallenge.emails.backends.CelerySESBackend"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "grandchallenge@localhost"
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "root@localhost")

ANONYMOUS_USER_NAME = "AnonymousUser"
USER_LOGIN_TIMEOUT_DAYS = 14
REGISTERED_USERS_GROUP_NAME = "__registered_users_group__"
REGISTERED_AND_ANON_USERS_GROUP_NAME = "__registered_and_anonymous_users__"
CHALLENGES_REVIEWERS_GROUP_NAME = "__challengerequest_reviewers__"

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

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Use AutoField for backwards compatibility
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DOCUMENTATION_HELP_VIEWER_CONTENT_SLUG = os.environ.get(
    "DOCUMENTATION_HELP_VIEWER_CONTENT_SLUG", "viewer-content"
)
DOCUMENTATION_HELP_INTERFACES_SLUG = os.environ.get(
    "DOCUMENTATION_HELP_INTERFACES_SLUG", "interfaces"
)

# About Flatpage
FLATPAGE_ABOUT_URL = os.environ.get("FLATPAGE_ABOUT_URL", "/about/")

# All costs exclude Tax
COMPONENTS_TAX_RATE_PERCENT = 0.21
if COMPONENTS_TAX_RATE_PERCENT > 1:
    raise ImproperlyConfigured("Tax rate should be less than 1")
COMPONENTS_USD_TO_EUR = float(
    os.environ.get("COMPONENTS_USD_TO_EUR", "0.92472705")
)
COMPONENTS_S3_USD_MILLICENTS_PER_YEAR_PER_TB = (
    12_300_000  # Last calculated 23/08/2023
)
COMPONENTS_ECR_USD_MILLICENTS_PER_YEAR_PER_TB = (
    39_600_000  # Last calculated 23/08/2023
)

CHALLENGE_BASE_COST_IN_EURO = int(
    os.environ.get("CHALLENGE_BASE_COST_IN_EURO", 5000)
)
CHALLENGE_MINIMAL_COMPUTE_AND_STORAGE_IN_EURO = int(
    os.environ.get("CHALLENGE_MINIMAL_COMPUTE_AND_STORAGE_IN_EURO", 1000)
)
CHALLENGE_ADDITIONAL_COMPUTE_AND_STORAGE_PACK_SIZE_IN_EURO = int(
    os.environ.get(
        "CHALLENGE_ADDITIONAL_COMPUTE_AND_STORAGE_PACK_SIZE_IN_EURO", 500
    )
)
CHALLENGE_NUM_SUPPORT_YEARS = int(
    os.environ.get("CHALLENGE_NUM_SUPPORT_YEARS", 5)
)

GCAPI_LATEST_VERSION = os.environ.get("GCAPI_LATEST_VERSION", "0.13.2")
GCAPI_LOWEST_SUPPORTED_VERSION = os.environ.get(
    "GCAPI_LOWEST_SUPPORTED_VERSION", "0.13.0"
)


##############################################################################
#
# Storage
#
##############################################################################
STORAGES = {
    "default": {
        "BACKEND": "grandchallenge.core.storage.PublicS3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Subdirectories on root for various files
IMAGE_FILES_SUBDIRECTORY = "images"
EVALUATION_FILES_SUBDIRECTORY = "evaluation"
EVALUATION_SUPPLEMENTARY_FILES_SUBDIRECTORY = "evaluation-supplementary"
COMPONENTS_FILES_SUBDIRECTORY = "components"

# Minio differs from s3, we know:
#  - Leading slashes are not respected in list_objects_v2
#  - sha256 sums are not implemented
USING_MINIO = strtobool(os.environ.get("USING_MINIO", "False"))

AWS_S3_FILE_OVERWRITE = False
# Note: deprecated in django storages 2.0
AWS_BUCKET_ACL = "private"
AWS_DEFAULT_ACL = "private"
AWS_S3_MAX_MEMORY_SIZE = 1_048_576  # 100 MB
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")
AWS_S3_URL_PROTOCOL = os.environ.get("AWS_S3_URL_PROTOCOL", "https:")
AWS_CLOUDWATCH_REGION_NAME = os.environ.get("AWS_CLOUDWATCH_REGION_NAME")
AWS_CODEBUILD_REGION_NAME = os.environ.get("AWS_CODEBUILD_REGION_NAME")
AWS_SES_REGION_NAME = os.environ.get("AWS_SES_REGION_NAME")

# This is for storing files that should not be served to the public
PRIVATE_S3_STORAGE_KWARGS = {
    "bucket_name": os.environ.get(
        "PRIVATE_S3_STORAGE_BUCKET_NAME", "grand-challenge-private"
    )
}

PROTECTED_S3_STORAGE_KWARGS = {
    "bucket_name": os.environ.get(
        "PROTECTED_S3_STORAGE_BUCKET_NAME", "grand-challenge-protected"
    ),
    # This is the domain where people will be able to go to download data
    # from this bucket. Usually we would use reverse to find this out,
    # but this needs to be defined before the database is populated
    "custom_domain": os.environ.get(
        "PROTECTED_S3_CUSTOM_DOMAIN", "gc.localhost/media"
    ),
}
PROTECTED_S3_STORAGE_USE_CLOUDFRONT = strtobool(
    os.environ.get("PROTECTED_S3_STORAGE_USE_CLOUDFRONT", "False")
)
PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN = os.environ.get(
    "PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN_NAME", ""
)

PUBLIC_FILE_CACHE_CONTROL = "max-age=315360000, public, immutable"

PUBLIC_S3_STORAGE_KWARGS = {
    "bucket_name": os.environ.get(
        "PUBLIC_S3_STORAGE_BUCKET_NAME", "grand-challenge-public"
    ),
    "custom_domain": os.environ.get("PUBLIC_S3_CUSTOM_DOMAIN"),
    # Public bucket so do not use querystring_auth
    "querystring_auth": False,
    "default_acl": os.environ.get("PUBLIC_S3_DEFAULT_ACL", "public-read"),
    "object_parameters": {"CacheControl": PUBLIC_FILE_CACHE_CONTROL},
}

UPLOADS_S3_BUCKET_NAME = os.environ.get(
    "UPLOADS_S3_BUCKET_NAME", "grand-challenge-uploads"
)
UPLOADS_S3_USE_ACCELERATE_ENDPOINT = strtobool(
    os.environ.get("UPLOADS_S3_USE_ACCELERATE_ENDPOINT", "False")
)
UPLOADS_MAX_SIZE_UNVERIFIED = int(
    os.environ.get("UPLOADS_MAX_SIZE_UNVERIFIED", 2 * GIGABYTE)
)
UPLOADS_MAX_SIZE_VERIFIED = int(
    os.environ.get("UPLOADS_MAX_SIZE_VERIFIED", 128 * GIGABYTE)
)
UPLOADS_TIMEOUT_DAYS = int(os.environ.get("UPLOADS_TIMEOUT_DAYS", 1))

VERIFICATIONS_REVIEW_PERIOD_DAYS = int(
    os.environ.get("VERIFICATIONS_REVIEW_PERIOD_DAYS", 10)
)
VERIFICATIONS_USER_SET_COOKIE_NAME = "vus"

# Key pair used for signing CloudFront URLS, only used if
# PROTECTED_S3_STORAGE_USE_CLOUDFRONT is True
CLOUDFRONT_KEY_PAIR_ID = os.environ.get("CLOUDFRONT_KEY_PAIR_ID", "")
CLOUDFRONT_PRIVATE_KEY_BASE64 = os.environ.get(
    "CLOUDFRONT_PRIVATE_KEY_BASE64", ""
)
CLOUDFRONT_URL_EXPIRY_SECONDS = int(
    os.environ.get("CLOUDFRONT_URL_EXPIRY_SECONDS", "300")  # 5 mins
)

##############################################################################
#
# Caching
#
##############################################################################
REDIS_ENDPOINT = os.environ.get("REDIS_ENDPOINT", "redis://redis:6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_ENDPOINT}/0",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

ROOT_URLCONF = "config.urls.root"
CHALLENGE_SUBDOMAIN_URL_CONF = "config.urls.challenge_subdomain"
RENDERING_SUBDOMAIN_URL_CONF = "config.urls.rendering_subdomain"

DEFAULT_SCHEME = os.environ.get("DEFAULT_SCHEME", "https")
SITE_SERVER_PORT = os.environ.get("SITE_SERVER_PORT")

SESSION_ENGINE = "grandchallenge.browser_sessions.models"
SESSION_PRIVILEGED_USER_TIMEOUT = timedelta(hours=8)
SESSION_COOKIE_DOMAIN = os.environ.get(
    "SESSION_COOKIE_DOMAIN", ".gc.localhost"
)
if not SESSION_COOKIE_DOMAIN.startswith("."):
    raise ImproperlyConfigured("SESSION_COOKIE_DOMAIN should start with a '.'")

SESSION_COOKIE_SECURE = strtobool(
    os.environ.get("SESSION_COOKIE_SECURE", "True")
)
CSRF_COOKIE_SECURE = strtobool(os.environ.get("CSRF_COOKIE_SECURE", "True"))
# Trust all subdomains for CSRF, used for user uploads. Changed the name
# of the CSRF token as existing ones are already in use.
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN
CSRF_COOKIE_NAME = "_csrftoken"
CSRF_TRUSTED_ORIGINS = [
    f"{DEFAULT_SCHEME}://*{SESSION_COOKIE_DOMAIN}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}"
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = strtobool(os.environ.get("SECURE_SSL_REDIRECT", "True"))

SECURE_CROSS_ORIGIN_OPENER_POLICY = os.environ.get(
    "SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin"
)


def get_private_ip():
    return socket.gethostbyname(socket.gethostname())


# Set the allowed hosts to the cookie domain
# Adding the private ip allows the health check to work
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN, get_private_ip()]

# Security options
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = strtobool(
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False")
)
SECURE_HSTS_PRELOAD = strtobool(os.environ.get("SECURE_HSTS_PRELOAD", "True"))
SECURE_CONTENT_TYPE_NOSNIFF = strtobool(
    os.environ.get("SECURE_CONTENT_TYPE_NOSNIFF", "False")
)
SECURE_BROWSER_XSS_FILTER = strtobool(
    os.environ.get("SECURE_BROWSER_XSS_FILTER", "False")
)
X_FRAME_OPTIONS = "DENY"
# "strict-origin-when-cross-origin" required for uploads for cross domain POSTs
SECURE_REFERRER_POLICY = os.environ.get(
    "SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin"
)

PERMISSIONS_POLICY = {
    "accelerometer": [],
    "ambient-light-sensor": [],
    "autoplay": [],
    "camera": [],
    "display-capture": [],
    "document-domain": [],
    "encrypted-media": [],
    "fullscreen": ["self"],
    "geolocation": [],
    "gyroscope": [],
    "interest-cohort": [],
    "magnetometer": [],
    "microphone": [],
    "midi": [],
    "payment": [],
    "usb": [],
}

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
STATIC_HOST = os.environ.get("DJANGO_STATIC_HOST", "")
STATIC_URL = f"{STATIC_HOST}/{COMMIT_ID}/"
STATIC_ROOT = safe_join(os.environ.get("STATIC_ROOT", "/static/"), COMMIT_ID)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",  # for css compression
)

# CSS Compression settings
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
LIBSASS_OUTPUT_STYLE = "compressed"
COMPRESS_OFFLINE = strtobool(os.environ.get("COMPRESS_OFFLINE", "True"))

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "d=%^l=xa02an9jn-$!*hy1)5yox$a-$2(ejt-2smimh=j4%8*b"
)

default_loaders = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

cached_loaders = [("django.template.loaders.cached.Loader", default_loaders)]

# Webpack Loader configuration
WEBPACK_LOADER = {
    "DEFAULT": {
        "BUNDLE_DIR_NAME": "npm_vendored/",
        "STATS_FILE": os.path.join(
            Path(__file__).resolve().parent.parent,
            "grandchallenge/core/static/npm_vendored/webpack-stats.json",
        ),
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
                "grandchallenge.core.context_processors.deployment_info",
                "grandchallenge.core.context_processors.debug",
                "grandchallenge.core.context_processors.sentry_dsn",
                "grandchallenge.core.context_processors.footer_links",
                "grandchallenge.core.context_processors.about_page",
                "grandchallenge.core.context_processors.newsletter_signup",
                "grandchallenge.core.context_processors.viewport_names",
                "grandchallenge.core.context_processors.workstation_domains",
            ],
            "loaders": default_loaders if DEBUG else cached_loaders,
        },
    }
]

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",  # Keep security at top
    "aws_xray_sdk.ext.django.middleware.XRayMiddleware",  # xray near the top
    "corsheaders.middleware.CorsMiddleware",  # Keep CORS near the top
    "csp.contrib.rate_limiting.RateLimitedCSPMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    # Keep BrokenLinkEmailsMiddleware near the top
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # subdomain_middleware after CurrentSiteMiddleware
    "grandchallenge.subdomains.middleware.subdomain_middleware",
    "grandchallenge.subdomains.middleware.challenge_subdomain_middleware",
    "grandchallenge.subdomains.middleware.subdomain_urlconf_middleware",
    "grandchallenge.timezones.middleware.TimezoneMiddleware",
    # Force 2FA for staff users
    "grandchallenge.core.middleware.RequireStaffAndSuperuser2FAMiddleware",
    # Flatpage fallback almost last
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    # Redirects last as they're a last resort
    "django.contrib.redirects.middleware.RedirectFallbackMiddleware",
)

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "config.wsgi.application"

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "grandchallenge.django_admin",  # Keep above django.contrib.admin
    "django.contrib.admin",
    "django.contrib.postgres",
    "django.contrib.flatpages",
    "django.contrib.sitemaps",
    "django.contrib.redirects",
    "django.forms",
]

THIRD_PARTY_APPS = [
    "aws_xray_sdk.ext.django",  # tracing
    "django_celery_results",  # database results backend
    "django_celery_beat",  # periodic tasks
    "guardian",  # per object permissions
    "rest_framework",  # provides REST API
    "knox",  # token auth for REST API
    "crispy_forms",  # bootstrap forms
    "crispy_bootstrap4",
    "django_select2",  # for multiple choice widgets
    "dal",  # for autocompletion of selection fields
    "dal_select2",  # for autocompletion of selection fields
    "django_extensions",  # custom extensions
    "corsheaders",  # to allow api communication from subdomains
    "markdownx",  # for editing markdown
    "compressor",  # for compressing css
    "webpack_loader",  # for webpack integration
    "stdimage",
    "django_filters",
    "drf_spectacular",
    "csp",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
    "grandchallenge.profiles.providers.gmail",
    # Notifications with overrides
    "actstream",
    "grandchallenge.notifications",
    # django-machina dependencies:
    "mptt",
    "haystack",
    "widget_tweaks",
    # djano-machina apps:
    "machina",
    "machina.apps.forum",
    "machina.apps.forum_conversation.forum_attachments",
    "machina.apps.forum_conversation.forum_polls",
    "machina.apps.forum_feeds",
    "machina.apps.forum_moderation",
    "machina.apps.forum_search",
    "machina.apps.forum_tracking",
    "machina.apps.forum_permission",
    # Overridden apps
    "grandchallenge.forum_conversation",
    "grandchallenge.forum_member",
]

LOCAL_APPS = [
    "grandchallenge.admins",
    "grandchallenge.anatomy",
    "grandchallenge.api",
    "grandchallenge.api_tokens",
    "grandchallenge.challenges",
    "grandchallenge.core",
    "grandchallenge.evaluation",
    "grandchallenge.pages",
    "grandchallenge.participants",
    "grandchallenge.profiles",
    "grandchallenge.teams",
    "grandchallenge.uploads",
    "grandchallenge.cases",
    "grandchallenge.algorithms",
    "grandchallenge.components",
    "grandchallenge.statistics",
    "grandchallenge.archives",
    "grandchallenge.workstations",
    "grandchallenge.reader_studies",
    "grandchallenge.workstation_configs",
    "grandchallenge.policies",
    "grandchallenge.serving",
    "grandchallenge.blogs",
    "grandchallenge.publications",
    "grandchallenge.verifications",
    "grandchallenge.task_categories",
    "grandchallenge.modalities",
    "grandchallenge.datatables",
    "grandchallenge.organizations",
    "grandchallenge.groups",
    "grandchallenge.github",
    "grandchallenge.codebuild",
    "grandchallenge.timezones",
    "grandchallenge.documentation",
    "grandchallenge.flatpages",
    "grandchallenge.emails",
    "grandchallenge.hanging_protocols",
    "grandchallenge.charts",
    "grandchallenge.forums",
    "grandchallenge.invoices",
    "grandchallenge.direct_messages",
    "grandchallenge.incentives",
    "grandchallenge.browser_sessions",
    "grandchallenge.well_known",
    "grandchallenge.utilization",
    "grandchallenge.discussion_forums",
]

LEGACY_APPS = [
    # Applications that can be removed when all instances are up-to-date
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS + LEGACY_APPS

ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "django-admin")

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]

##############################################################################
#
# django-allauth
# https://docs.allauth.org/en/latest/account/configuration.html
# https://docs.allauth.org/en/latest/socialaccount/configuration.html
# https://docs.allauth.org/en/latest/mfa/configuration.html
# https://docs.allauth.org/en/latest/usersessions/configuration.html
# https://docs.allauth.org/en/latest/common/configuration.html
#
##############################################################################

ACCOUNT_ADAPTER = "grandchallenge.profiles.adapters.AccountAdapter"
ACCOUNT_SIGNUP_FORM_CLASS = "grandchallenge.profiles.forms.SignupForm"

ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = [
    "username*",
    "email*",
    "email2*",
    "password1*",
    "password2*",
]
ACCOUNT_EMAIL_NOTIFICATIONS = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = "phone_number"
ACCOUNT_CHANGE_EMAIL = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_REAUTHENTICATION_REQUIRED = True
ACCOUNT_REAUTHENTICATION_TIMEOUT = 120
ACCOUNT_USERNAME_MIN_LENGTH = 4
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USERNAME_BLACKLIST = USERNAME_DENYLIST
ACCOUNT_USERNAME_VALIDATORS = (
    "grandchallenge.profiles.validators.username_validators"
)

SOCIALACCOUNT_ADAPTER = "grandchallenge.profiles.adapters.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "gmail": {
        "APP": {
            "client_id": os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", ""),
            "secret": os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", ""),
        },
        # Require confirmation of email due to problems with spam users
        "VERIFIED_EMAIL": False,
    }
}

# Use full paths as view name lookups do not work on subdomains
LOGIN_URL = "/accounts/login/"
LOGOUT_URL = "/accounts/logout/"
LOGIN_REDIRECT_URL = "/users/profile/"

##############################################################################
#
# stdimage
#
##############################################################################

# Re-render the existing images if these values change
# https://github.com/codingjoe/django-stdimage#re-rendering-variations
STDIMAGE_LOGO_VARIATIONS = {
    # Must be square
    "full": (None, None, False),
    "x20": (640, 640, True),
    "x15": (480, 480, True),
    "x10": (320, 320, True),
    "x02": (64, 64, True),
}
STDIMAGE_SOCIAL_VARIATIONS = {
    # Values from social sharing
    "full": (None, None, False),
    "x20": (1280, 640, False),
    "x15": (960, 480, False),
    "x10": (640, 320, False),
}
STDIMAGE_BANNER_VARIATIONS = {
    # Fixed width, any height
    "full": (None, None, False),
    "x20": (2220, None, False),
    "x15": (1665, None, False),
    "x10": (1110, None, False),
}

##############################################################################
#
# actstream
#
##############################################################################

ACTSTREAM_ENABLE = strtobool(os.environ.get("ACTSTREAM_ENABLE", "True"))
ACTSTREAM_SETTINGS = {
    "MANAGER": "actstream.managers.ActionManager",
    "FETCH_RELATIONS": True,
    "USE_JSONFIELD": True,
}

##############################################################################
#
# bleach
#
##############################################################################

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
    "del",
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
    "sub",
    "table",
    "tbody",
    "thead",
    "td",
    "th",
    "tr",
    "u",
    "ul",
    "video",
]
BLEACH_ALLOWED_ATTRIBUTES = {
    "*": ["class", "data-toggle", "id", "style", "role"],
    "a": ["href", "title", "target", "rel", "data-target"],
    "abbr": ["title"],
    "acronym": ["title"],
    "img": ["height", "src", "width"],
    # For bootstrap tables: https://getbootstrap.com/docs/4.3/content/tables/
    "th": ["scope", "colspan"],
    "td": ["colspan"],
    "video": ["src", "loop", "controls", "poster"],
}
BLEACH_ALLOWED_STYLES = ["height", "width"]
BLEACH_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
BLEACH_STRIP = strtobool(os.environ.get("BLEACH_STRIP", "True"))

# The markdown processor
MARKDOWNX_MEDIA_PATH = now().strftime("i/%Y/%m/%d/")
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    "markdown.extensions.attr_list",
    "markdown.extensions.codehilite",
    "markdown.extensions.fenced_code",
    "markdown.extensions.md_in_html",
    "markdown.extensions.sane_lists",
    "markdown.extensions.tables",
    "pymdownx.betterem",
    "pymdownx.magiclink",
    "pymdownx.tasklist",
    "pymdownx.tilde",
    BS4Extension(),
]
MARKDOWN_POST_PROCESSORS = []
MARKDOWNX_MARKDOWNIFY_FUNCTION = (
    "grandchallenge.core.templatetags.bleach.md2html"
)
MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS = {
    "markdown.extensions.codehilite": {
        "wrapcode": False,
    }
}
MARKDOWNX_IMAGE_MAX_SIZE = {"size": (2000, 0), "quality": 90}
MARKDOWNX_EDITOR_RESIZABLE = "False"

HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"}
}

FORUMS_MIN_ACCOUNT_AGE_DAYS = int(
    os.environ.get("FORUMS_MIN_ACCOUNT_AGE_DAYS", "2")
)

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
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {
        "level": os.environ.get("GRAND_CHALLENGE_LOG_LEVEL", "INFO"),
        "handlers": ["console"],
    },
    "loggers": {
        # As AWS_XRAY_CONTEXT_MISSING can only be set to LOG_ERROR,
        # silence errors from this sdk as they flood the logs in
        # RedirectFallbackMiddleware
        "aws_xray_sdk": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}

###############################################################################
# SENTRY
###############################################################################

SENTRY_DSN = os.environ.get("DJANGO_SENTRY_DSN", "")
SENTRY_ENABLE_JS_REPORTING = strtobool(
    os.environ.get("SENTRY_ENABLE_JS_REPORTING", "False")
)
WORKSTATION_SENTRY_DSN = os.environ.get("WORKSTATION_SENTRY_DSN", "")

if SENTRY_DSN:

    def sentry_before_send(event, hint):
        """Add stderr to the event if the exception is a CalledProcessError"""
        if "exc_info" in hint:
            exc_type, exc_value, tb = hint["exc_info"]

            if isinstance(exc_value, CalledProcessError) and hasattr(
                exc_value, "stderr"
            ):
                event["extra"] = event.get("extra", {})

                if isinstance(exc_value.stderr, str):
                    event["extra"]["stderr"] = exc_value.stderr
                elif isinstance(exc_value.stderr, bytes):
                    event["extra"]["stderr"] = exc_value.stderr.decode(
                        "utf-8", "replace"
                    )
                else:
                    # Do not include stderr
                    pass

        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        release=COMMIT_ID,
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
        ),
        ignore_errors=[PriorStepFailed],
        before_send=sentry_before_send,
    )
    ignore_logger("django.security.DisallowedHost")
    ignore_logger("aws_xray_sdk")

###############################################################################
# XRAY
###############################################################################
XRAY_RECORDER = {
    "AWS_XRAY_CONTEXT_MISSING": "LOG_ERROR",
    "PLUGINS": ("ECSPlugin",),
    "AWS_XRAY_TRACING_NAME": SESSION_COOKIE_DOMAIN.lstrip("."),
}

###############################################################################
#
# django-rest-framework and drf-spectacular
#
###############################################################################

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAdminUser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "knox.auth.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "grandchallenge.api.pagination.MaxLimit1000OffsetPagination",
    "PAGE_SIZE": 100,
    "UNAUTHENTICATED_USER": "guardian.utils.get_anonymous_user",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "TITLE": f"{SESSION_COOKIE_DOMAIN.lstrip('.')} API",
    "DESCRIPTION": f"The API for {SESSION_COOKIE_DOMAIN.lstrip('.')}.",
    "TOS": f"https://{SESSION_COOKIE_DOMAIN.lstrip('.')}/policies/terms-of-service/",
    "LICENSE": {"name": "Apache License 2.0"},
    "VERSION": "1.0.0",
    "ENUM_NAME_OVERRIDES": {
        "ColorInterpolationEnum": "grandchallenge.workstation_configs.models.LookUpTable.COLOR_INTERPOLATION_CHOICES",
    },
    "COMPONENT_SPLIT_REQUEST": True,
}

###############################################################################
#
# CORS
#
###############################################################################

VALID_SUBDOMAIN_REGEX = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
CORS_ALLOWED_ORIGIN_REGEXES = [
    rf"^{DEFAULT_SCHEME}:\/\/{VALID_SUBDOMAIN_REGEX}{re.escape(SESSION_COOKIE_DOMAIN)}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}$",
]
# SESSION_COOKIE_SAMESITE should be set to "lax" so won't send credentials
# across domains, but this will allow workstations to access the api
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    *default_headers,
    "hx-trigger",
    "hx-target",
    "hx-current-url",
    "hx-request",
    "hx-trigger-name",
)

###############################################################################
#
# celery
#
###############################################################################

CELERY_SOLO_QUEUES = {
    element
    for queue in {"acks-late-2xlarge", "acks-late-micro-short"}
    for element in {queue, f"{queue}-delay"}
}
CELERY_WORKER_MAX_MEMORY_MB = int(
    os.environ.get("CELERY_WORKER_MAX_MEMORY_MB", "0")
)
ECS_ENABLE_CELERY_SCALE_IN_PROTECTION = strtobool(
    os.environ.get("ECS_ENABLE_CELERY_SCALE_IN_PROTECTION", "False"),
)

CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "django-db")
CELERY_RESULT_PERSISTENT = True
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 0  # We handle cleanup of results ourselves
CELERY_TASK_ACKS_LATE = strtobool(
    os.environ.get("CELERY_TASK_ACKS_LATE", "False")
)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(
    os.environ.get("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")
)
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "7200"))
# The soft time limit must always be shorter than the hard time limit
# https://github.com/celery/celery/issues/9125
CELERY_TASK_SOFT_TIME_LIMIT = int(0.9 * CELERY_TASK_TIME_LIMIT)
CELERY_TASK_TRACK_STARTED = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": int(1.1 * CELERY_TASK_TIME_LIMIT)
}
CELERY_BROKER_CONNECTION_MAX_RETRIES = 0
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

if os.environ.get("BROKER_TYPE", "").lower() == "sqs":
    CELERY_BROKER_URL = "sqs://"

    CELERY_WORKER_ENABLE_REMOTE_CONTROL = False
    CELERY_BROKER_USE_SSL = True

    CELERY_BROKER_TRANSPORT_OPTIONS.update(
        {
            "queue_name_prefix": os.environ.get(
                "CELERY_BROKER_QUEUE_NAME_PREFIX", "gclocalhost-"
            ),
            "region": os.environ.get(
                "CELERY_BROKER_REGION", AWS_DEFAULT_REGION
            ),
            "polling_interval": int(
                os.environ.get("CELERY_BROKER_POLLING_INTERVAL", "1")
            ),
        }
    )
else:
    CELERY_BROKER_URL = os.environ.get("BROKER_URL", f"{REDIS_ENDPOINT}/1")

COMPONENTS_DEFAULT_BACKEND = os.environ.get(
    "COMPONENTS_DEFAULT_BACKEND",
    "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor",
)
COMPONENTS_REGISTRY_URL = os.environ.get(
    "COMPONENTS_REGISTRY_URL", "registry:5000"
)
COMPONENTS_REGISTRY_PREFIX = os.environ.get(
    "COMPONENTS_REGISTRY_PREFIX", SESSION_COOKIE_DOMAIN.lstrip(".")
)
COMPONENTS_REGISTRY_INSECURE = strtobool(
    os.environ.get("COMPONENTS_REGISTRY_INSECURE", "False")
)
COMPONENTS_SAGEMAKER_SHIM_VERSION = os.environ.get(
    "COMPONENTS_SAGEMAKER_SHIM_VERSION"
)
COMPONENTS_SAGEMAKER_SHIM_LOCATION = os.environ.get(
    "COMPONENTS_SAGEMAKER_SHIM_LOCATION", "/opt/sagemaker-shim"
)
COMPONENTS_USE_WARM_POOL = strtobool(
    os.environ.get("COMPONENTS_USE_WARM_POOL", "True")
)
COMPONENTS_INPUT_BUCKET_NAME = os.environ.get(
    "COMPONENTS_INPUT_BUCKET_NAME", "grand-challenge-components-inputs"
)
COMPONENTS_OUTPUT_BUCKET_NAME = os.environ.get(
    "COMPONENTS_OUTPUT_BUCKET_NAME", "grand-challenge-components-outputs"
)
COMPONENTS_MAXIMUM_IMAGE_SIZE = 10 * GIGABYTE
COMPONENTS_MINIMUM_JOB_DURATION = 5 * 60  # 5 minutes
COMPONENTS_MAXIMUM_JOB_DURATION = 24 * 60 * 60  # 24 hours
COMPONENTS_AMAZON_ECR_REGION = os.environ.get("COMPONENTS_AMAZON_ECR_REGION")
COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN = os.environ.get(
    "COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN", ""
)
COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID = os.environ.get(
    "COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID", ""
)
COMPONENTS_AMAZON_SAGEMAKER_SUBNETS = os.environ.get(
    "COMPONENTS_AMAZON_SAGEMAKER_SUBNETS", ""
).split(",")
COMPONENTS_S3_ENDPOINT_URL = os.environ.get(
    "COMPONENTS_S3_ENDPOINT_URL", AWS_S3_ENDPOINT_URL
)
COMPONENTS_DOCKER_NETWORK_NAME = os.environ.get(
    "COMPONENTS_DOCKER_NETWORK_NAME", "grand-challengeorg_components"
)
COMPONENTS_DOCKER_TASK_SET_AWS_ENV = strtobool(
    os.environ.get("COMPONENTS_DOCKER_TASK_SET_AWS_ENV", "True")
)
COMPONENTS_DOCKER_TASK_AWS_ACCESS_KEY_ID = os.environ.get(
    "COMPONENTS_DOCKER_TASK_AWS_ACCESS_KEY_ID", "componentstask"
)
COMPONENTS_DOCKER_TASK_AWS_SECRET_ACCESS_KEY = os.environ.get(
    "COMPONENTS_DOCKER_TASK_AWS_SECRET_ACCESS_KEY", "componentstask123"
)
COMPONENTS_DOCKER_KEEP_CAPS_UNSAFE = strtobool(
    os.environ.get("COMPONENTS_DOCKER_KEEP_CAPS_UNSAFE", "False")
)
COMPONENTS_PUBLISH_PORTS = strtobool(
    os.environ.get("COMPONENTS_PUBLISH_PORTS", "False")
)
COMPONENTS_PORT_ADDRESS = os.environ.get("COMPONENTS_PORT_ADDRESS", "0.0.0.0")

COMPONENTS_MEMORY_LIMIT = int(os.environ.get("COMPONENTS_MEMORY_LIMIT", "4"))
COMPONENTS_CPU_QUOTA = int(os.environ.get("COMPONENTS_CPU_QUOTA", "100000"))
COMPONENTS_CPU_PERIOD = int(os.environ.get("COMPONENTS_CPU_PERIOD", "100000"))
COMPONENTS_PIDS_LIMIT = int(os.environ.get("COMPONENTS_PIDS_LIMIT", "128"))
COMPONENTS_CPU_SHARES = int(
    os.environ.get("COMPONENTS_CPU_SHARES", "1024")  # Default weight
)
COMPONENTS_CPUSET_CPUS = str(os.environ.get("COMPONENTS_CPUSET_CPUS", ""))
COMPONENTS_DOCKER_RUNTIME = os.environ.get("COMPONENTS_DOCKER_RUNTIME", None)
COMPONENTS_NVIDIA_VISIBLE_DEVICES = os.environ.get(
    "COMPONENTS_NVIDIA_VISIBLE_DEVICES", "void"
)
COMPONENTS_CONTAINER_PLATFORM = "linux/amd64"

COMPONENTS_VIRTUAL_ENV_BIOM_LOCATION = os.environ.get(
    "COMPONENTS_VIRTUAL_ENV_BIOM_LOCATION", "/opt/virtualenvs/biom"
)
# Set which template pack to use for forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# When using bootstrap error messages need to be renamed to danger
MESSAGE_TAGS = {messages.ERROR: "danger"}

# The name of the group whose members will be able to create reader studies
READER_STUDY_CREATORS_GROUP_NAME = "reader_study_creators"

###############################################################################
#
# challenges
#
###############################################################################

CHALLENGES_DEFAULT_ACTIVE_MONTHS = 12
CHALLENGE_ONBOARDING_TASKS_OVERDUE_SOON_CUTOFF = timedelta(days=7)
CHALLENGE_INVOICE_OVERDUE_CUTOFF = timedelta(weeks=4)

###############################################################################
#
# workstations
#
###############################################################################

# The workstation that is accessible by all authorised users
DEFAULT_WORKSTATION_SLUG = os.environ.get(
    "DEFAULT_WORKSTATION_SLUG", "cirrus-core"
)
WORKSTATIONS_BASE_IMAGE_PATH_PARAM = "image"
WORKSTATIONS_READY_STUDY_PATH_PARAM = "reader-study"
WORKSTATIONS_ALGORITHM_JOB_PATH_PARAM = "algorithm-job"
WORKSTATIONS_ARCHIVE_ITEM_PATH_PARAM = "archive-item"
WORKSTATIONS_CONFIG_QUERY_PARAM = "config"
WORKSTATIONS_USER_QUERY_PARAM = "viewAsUser"
WORKSTATIONS_DISPLAY_SET_PATH_PARAM = "display-set"
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
# Which regions are available for workstations to run in
WORKSTATIONS_ACTIVE_REGIONS = os.environ.get(
    "WORKSTATIONS_ACTIVE_REGIONS", AWS_DEFAULT_REGION
).split(",")
WORKSTATIONS_RENDERING_SUBDOMAINS = {
    # Possible AWS regions
    *[
        "-".join(z)
        for z in product(
            ["us", "af", "ap", "ca", "cn", "eu", "me", "sa"],
            [
                "east",
                "west",
                "south",
                "north",
                "central",
                "northeast",
                "southeast",
                "northwest",
                "southwest",
            ],
            ["1", "2", "3"],
        )
    ],
    # User defined regions
    "eu-nl-1",
    "eu-nl-2",
}
# Number of minutes grace period before the container is stopped
WORKSTATIONS_GRACE_MINUTES = 5

# Extra domains to broadcast workstation control messages to. Used in tests.
WORKSTATIONS_EXTRA_BROADCAST_DOMAINS = []

# The limit on concurrent API requests for each workstation session
WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS = int(
    os.environ.get("WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS", 10)
)

INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS = json.loads(
    os.environ.get("INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS", "null")
)

EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS = int(
    os.environ.get("EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS", 86400)
)

CELERY_BEAT_SCHEDULE = {
    "refresh_expiring_user_tokens": {
        "task": "grandchallenge.github.tasks.refresh_expiring_user_tokens",
        "schedule": crontab(hour=0, minute=15),
    },
    "update_publication_metadata": {
        "task": "grandchallenge.publications.tasks.update_publication_metadata",
        "schedule": crontab(hour=0, minute=30),
    },
    "remove_inactive_container_images": {
        "task": "grandchallenge.components.tasks.remove_inactive_container_images",
        "schedule": crontab(hour=1, minute=0),
    },
    "delete_failed_import_container_images": {
        "task": "grandchallenge.components.tasks.delete_failed_import_container_images",
        "schedule": crontab(hour=1, minute=30),
    },
    "delete_old_unsuccessful_container_images": {
        "task": "grandchallenge.components.tasks.delete_old_unsuccessful_container_images",
        "schedule": crontab(hour=2, minute=0),
    },
    "update_associated_challenges": {
        "task": "grandchallenge.algorithms.tasks.update_associated_challenges",
        "schedule": crontab(hour=3, minute=0),
    },
    "send_new_unread_direct_messages_emails": {
        "task": "grandchallenge.direct_messages.tasks.send_new_unread_direct_messages_emails",
        "schedule": crontab(hour=3, minute=30),
    },
    "send_unread_notification_emails": {
        "task": "grandchallenge.notifications.tasks.send_unread_notification_emails",
        "schedule": crontab(hour=4, minute=0),
    },
    "update_site_statistics": {
        "task": "grandchallenge.statistics.tasks.update_site_statistics_cache",
        "schedule": crontab(hour=5, minute=30),
    },
    "send_onboarding_task_reminder_emails": {
        "task": "grandchallenge.challenges.tasks.send_onboarding_task_reminder_emails",
        "schedule": crontab(day_of_week="mon", hour=6, minute=0),
    },
    "send_challenge_invoice_overdue_reminder_emails": {
        "task": "grandchallenge.invoices.tasks.send_challenge_invoice_overdue_reminder_emails",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),
    },
    "update_challenge_storage_size": {
        "task": "grandchallenge.challenges.tasks.update_challenge_storage_size",
        "schedule": crontab(hour=6, minute=15),
    },
    "create_job_warm_pool_utilizations": {
        "task": "grandchallenge.utilization.tasks.create_job_warm_pool_utilizations",
        "schedule": crontab(minute=30),
    },
    "update_challenge_compute_costs": {
        "task": "grandchallenge.challenges.tasks.update_challenge_compute_costs",
        "schedule": crontab(minute=45),
    },
    "delete_users_who_dont_login": {
        "task": "grandchallenge.profiles.tasks.delete_users_who_dont_login",
        "schedule": timedelta(hours=1),
    },
    "delete_old_user_uploads": {
        "task": "grandchallenge.uploads.tasks.delete_old_user_uploads",
        "schedule": timedelta(hours=1),
    },
    "clear_sessions": {
        "task": "grandchallenge.browser_sessions.tasks.clear_sessions",
        "schedule": timedelta(hours=1),
    },
    "cleanup_expired_tokens": {
        "task": "grandchallenge.github.tasks.cleanup_expired_tokens",
        "schedule": timedelta(hours=1),
    },
    "cleanup_sent_raw_emails": {
        "task": "grandchallenge.emails.tasks.cleanup_sent_raw_emails",
        "schedule": timedelta(hours=1),
    },
    "cleanup_celery_backend": {
        "task": "grandchallenge.core.tasks.cleanup_celery_backend",
        "schedule": timedelta(hours=1),
    },
    "logout_privileged_users": {
        "task": "grandchallenge.browser_sessions.tasks.logout_privileged_users",
        "schedule": timedelta(hours=1),
    },
    "update_challenge_results_cache": {
        "task": "grandchallenge.challenges.tasks.update_challenge_results_cache",
        "schedule": timedelta(minutes=5),
    },
    "send_raw_emails": {
        "task": "grandchallenge.emails.tasks.send_raw_emails",
        "schedule": timedelta(seconds=30),
    },
    "cancel_external_evaluations_past_timeout": {
        "task": "grandchallenge.evaluation.tasks.cancel_external_evaluations_past_timeout",
        "schedule": timedelta(hours=1),
    },
    "push_metrics_to_cloudwatch": {
        "task": "grandchallenge.core.tasks.put_cloudwatch_metrics",
        "schedule": timedelta(seconds=30),
    },
    **{
        f"stop_expired_services_{region}": {
            "task": "grandchallenge.components.tasks.stop_expired_services",
            "kwargs": {
                "app_label": "workstations",
                "model_name": "session",
                "region": region,
            },
            "options": {"queue": f"workstations-{region}"},
            "schedule": timedelta(minutes=WORKSTATIONS_GRACE_MINUTES),
        }
        for region in WORKSTATIONS_ACTIVE_REGIONS
    },
    **{
        f"preload_interactive_algorithms_{region}": {
            "task": "grandchallenge.components.tasks.preload_interactive_algorithms",
            "options": {"queue": f"workstations-{region}"},
            "schedule": timedelta(minutes=WORKSTATIONS_GRACE_MINUTES),
        }
        for region in WORKSTATIONS_ACTIVE_REGIONS
    },
}

PUSH_CLOUDWATCH_METRICS = strtobool(
    os.environ.get("PUSH_CLOUDWATCH_METRICS", "False")
)

# The name of the group whose members will be able to create algorithms
ALGORITHMS_CREATORS_GROUP_NAME = "algorithm_creators"
ALGORITHMS_MAX_ACTIVE_JOBS = int(
    # The maximum number of active jobs for the entire system
    os.environ.get("ALGORITHMS_MAX_ACTIVE_JOBS", "128")
)
ALGORITHMS_MAX_ACTIVE_JOBS_PER_ALGORITHM = int(
    # The maximum number of active jobs for an algorithm
    os.environ.get("ALGORITHMS_MAX_ACTIVE_JOBS_PER_ALGORITHM", "16")
)
ALGORITHMS_MAX_ACTIVE_JOBS_PER_USER = int(
    # The maximum number of active jobs for a user
    os.environ.get("ALGORITHMS_MAX_ACTIVE_JOBS_PER_USER", "16")
)
# Maximum and minimum values the user can set for algorithm requirements
ALGORITHMS_MIN_MEMORY_GB = 4
ALGORITHMS_MAX_MEMORY_GB = 32
# The SageMaker Training backend has a maximum limit of 28 Days
ALGORITHMS_JOB_DEFAULT_TIME_LIMIT_SECONDS = os.environ.get(
    "ALGORITHMS_JOB_DEFAULT_TIME_LIMIT_SECONDS", "3600"
)
# How many cents per month each user receives by default
ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = int(
    os.environ.get("ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER", "1000")
)
ALGORITHMS_GENERAL_CENTS_PER_MONTH_PER_USER = int(
    os.environ.get("ALGORITHMS_GENERAL_CENTS_PER_MONTH_PER_USER", "1000")
)
ALGORITHMS_MAX_GENERAL_JOBS_PER_MONTH_PER_USER = int(
    os.environ.get("ALGORITHMS_MAX_GENERAL_JOBS_PER_MONTH_PER_USER", "50")
)
ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE = int(
    os.environ.get("ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE", "3")
)
ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS = int(
    os.environ.get("ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS", "5")
)

# Disallow some challenge names due to subdomain or media folder clashes
DISALLOWED_CHALLENGE_NAMES = {
    "m",
    IMAGE_FILES_SUBDIRECTORY,
    "logos",
    "banners",
    "mugshots",
    "docker",
    EVALUATION_FILES_SUBDIRECTORY,
    EVALUATION_SUPPLEMENTARY_FILES_SUBDIRECTORY,
    "favicon",
    "i",
    "cache",
    "challenge",
    "challenges",
    "static",
    *USERNAME_DENYLIST,
    *WORKSTATIONS_RENDERING_SUBDOMAINS,
}

# Disallow registration from certain domains
DISALLOWED_EMAIL_DOMAINS = {
    "qq.com",
    "aol.com",
    "usa.com",
    "yahoo.com",
    "yahoo.co.uk",
    "yahoo.it",
    "seznam.cz",
    "web.de",
    "gmx.de",
    "mail.com",
    "mail.ru",
    "verizon.net",
    "comcast.net",
    "inbox.ru",
    "hotmail.com",
    "outlook.com",
    "temporam.com",
    "mona.edu.kg",
    "mona.edu.pl",
    "zl.edu.kg",
    "lw.edu.kg",
    "edumail.edu.pl",
    *blocklist,
}

# GitHub App
GITHUB_APP_INSTALL_URL = os.environ.get("GITHUB_APP_INSTALL_URL", "")
GITHUB_APP_ID = os.environ.get("GITHUB_APP_ID", "")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_PRIVATE_KEY_BASE64 = os.environ.get("GITHUB_PRIVATE_KEY_BASE64", "")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

CODEBUILD_PROJECT_NAME = os.environ.get("CODEBUILD_PROJECT_NAME", "")
CODEBUILD_BUILD_LOGS_GROUP_NAME = os.environ.get(
    "CODEBUILD_BUILD_LOGS_GROUP_NAME", ""
)
CODEBUILD_ARTIFACTS_BUCKET_NAME = os.environ.get(
    "CODEBUILD_ARTIFACTS_BUCKET_NAME", ""
)

# Statistics App
STATISTICS_SITE_CACHE_KEY = "statistics/site_statistics"

# License keys from https://github.com/licensee/licensee/tree/v9.15.1/vendor/choosealicense.com/_licenses
OPEN_SOURCE_LICENSES = frozenset(
    (
        "agpl-3.0",
        "apache-2.0",
        "bsd-2-clause",
        "bsd-3-clause",
        "bsd-3-clause-clear",
        "bsd-4-clause",
        "bsl-1.0",
        "gpl-3.0",
        "lgpl-3.0",
        "mit",
        "mpl-2.0",
        "unlicense",
    )
)

# Set the post processors to use for the image imports
CASES_POST_PROCESSORS = os.environ.get(
    "CASES_POST_PROCESSORS", "panimg.post_processors.tiff_to_dzi"
).split(",")

# Maximum file size in bytes to be opened by SimpleITK.ReadImage in Image.sitk_image
MAX_SITK_FILE_SIZE = 256 * MEGABYTE

# The maximum size of all the files in an upload session in bytes
UPLOAD_SESSION_MAX_BYTES = 10 * GIGABYTE

# Some forms have a lot of data, such as a reader study update view
# that can contain reports about the medical images
DATA_UPLOAD_MAX_MEMORY_SIZE = 16 * MEGABYTE

# Some forms have a lot of fields, such as uploads of images
# with many slices
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(
    os.environ.get("DATA_UPLOAD_MAX_NUMBER_FIELDS", "2048")
)


##########################
# JSON SCHEMA
##########################
ALLOWED_JSON_SCHEMA_REF_SRC_REGEXES = (
    "https://vega.github.io/schema/vega-lite/v5.json",
)


##########################
# CONTENT SECURITY POLICY
##########################

CSP_STATIC_HOST = STATIC_HOST if STATIC_HOST else csp_constants.SELF

if AWS_S3_ENDPOINT_URL:
    CSP_MEDIA_HOSTS = (AWS_S3_ENDPOINT_URL,)
elif public_bucket_custom_domain := PUBLIC_S3_STORAGE_KWARGS["custom_domain"]:
    CSP_MEDIA_HOSTS = (f"https://{public_bucket_custom_domain}",)
else:
    CSP_MEDIA_HOSTS = (
        f"https://{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}.s3.amazonaws.com",
        f"https://{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}.s3.{AWS_DEFAULT_REGION}.amazonaws.com",
    )

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": csp_constants.NONE,
        "script-src": (
            CSP_STATIC_HOST,
            "'unsafe-eval'",  # Required for vega https://github.com/vega/vega/issues/1106
            csp_constants.SELF,  # Used in the Django admin
        ),
        "style-src": (
            CSP_STATIC_HOST,
            "https://fonts.googleapis.com",
            "'unsafe-inline'",  # TODO fix inline styles
        ),
        "font-src": (
            CSP_STATIC_HOST,
            "https://fonts.gstatic.com",
        ),
        "img-src": (
            CSP_STATIC_HOST,
            *CSP_MEDIA_HOSTS,
            "https://www.gravatar.com",  # Used for default mugshots
            "data:",  # Used by jsoneditor
            csp_constants.SELF,  # Used by Open Sea Dragon
            "https:",  # Arbitrary files used on blog posts and challenge pages
        ),
        "frame-src": (
            "https://www.youtube-nocookie.com",  # Embedding YouTube videos
        ),
        "media-src": (
            *CSP_MEDIA_HOSTS,
            "https://user-images.githubusercontent.com",  # Used in blog posts
        ),
        "connect-src": (
            csp_constants.SELF,  # For subdomain leaderboards
            # For workstation subdomain to main
            f"{DEFAULT_SCHEME}://{SESSION_COOKIE_DOMAIN.lstrip('.')}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}",
            # For main to workstation subdomain
            *(
                f"{DEFAULT_SCHEME}://{region}{SESSION_COOKIE_DOMAIN}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}"
                for region in WORKSTATIONS_ACTIVE_REGIONS
            ),
            "https://*.ingest.sentry.io",  # For Sentry errors
        ),
        "report-uri": os.environ.get("CSP_REPORT_URI"),
    },
    "REPORT_PERCENTAGE": float(os.environ.get("CSP_REPORT_PERCENTAGE", "0")),
}


if STATIC_HOST:
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += (
        STATIC_HOST,
    )  # For the map json

if PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN:
    # Used by Open Sea Dragon and countries json
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["img-src"] += (
        f"https://{PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}",
    )
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += (
        f"https://{PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}",
    )

if UPLOADS_S3_USE_ACCELERATE_ENDPOINT:
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += (
        f"https://{UPLOADS_S3_BUCKET_NAME}.s3-accelerate.amazonaws.com",
    )
else:
    if AWS_S3_ENDPOINT_URL:
        CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += (
            AWS_S3_ENDPOINT_URL,
        )
    else:
        CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += (
            f"https://{UPLOADS_S3_BUCKET_NAME}.s3.{AWS_DEFAULT_REGION}.amazonaws.com",
        )

if strtobool(os.environ.get("CSP_REPORT_ONLY", "False")):
    CONTENT_SECURITY_POLICY_REPORT_ONLY = CONTENT_SECURITY_POLICY
    del CONTENT_SECURITY_POLICY

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    # Allow localhost in development
    CORS_ALLOWED_ORIGIN_REGEXES += [r"^http://localhost:8888$"]

    if ENABLE_DEBUG_TOOLBAR:
        INSTALLED_APPS += ("debug_toolbar",)

        MIDDLEWARE = (
            "debug_toolbar.middleware.DebugToolbarMiddleware",
            *MIDDLEWARE,
        )

        DEBUG_TOOLBAR_CONFIG = {
            "SHOW_TOOLBAR_CALLBACK": "config.toolbar_callback",
            "RESULTS_CACHE_SIZE": 100,
        }
