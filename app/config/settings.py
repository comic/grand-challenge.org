import os
import re
from datetime import datetime, timedelta
from itertools import product
from pathlib import Path

import sentry_sdk
from celery.schedules import crontab
from disposable_email_domains import blocklist
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from machina import MACHINA_MAIN_STATIC_DIR, MACHINA_MAIN_TEMPLATE_DIR
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "grandchallenge"),
        "USER": os.environ.get("POSTGRES_USER", "grandchallenge"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "secretpassword"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", ""),
        "OPTIONS": {
            "sslmode": os.environ.get("POSTGRES_SSL_MODE", "prefer"),
            "sslrootcert": os.path.join(
                SITE_ROOT, "config", "certs", "rds-ca-2019-root.pem"
            ),
        },
        "ATOMIC_REQUESTS": strtobool(
            os.environ.get("ATOMIC_REQUESTS", "True")
        ),
    }
}

EMAIL_BACKEND = "djcelery_email.backends.CeleryEmailBackend"
CELERY_EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "grandchallenge@localhost"
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "root@localhost")

ANONYMOUS_USER_NAME = "AnonymousUser"
USER_LOGIN_TIMEOUT_DAYS = 14
REGISTERED_USERS_GROUP_NAME = "__registered_users_group__"
REGISTERED_AND_ANON_USERS_GROUP_NAME = "__registered_and_anonymous_users__"

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

# General forum
DOCUMENTATION_HELP_FORUM_PK = os.environ.get(
    "DOCUMENTATION_HELP_FORUM_PK", "1"
)
DOCUMENTATION_HELP_FORUM_SLUG = os.environ.get(
    "DOCUMENTATION_HELP_FORUM_SLUG", "general"
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

# Costs (in US dollar cents)
# based on 0.023 / GB / month S3 standard pricing
CHALLENGES_S3_STORAGE_COST_CENTS_PER_TB_PER_YEAR = int(
    os.environ.get("CHALLENGES_S3_STORAGE_COST_CENTS_PER_TB_PER_YEAR", 27600)
)
# based on cost calculation by James on 21.12.2022
CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR = int(
    os.environ.get("CHALLENGES_ECR_STORAGE_COST_CENTS_PER_TB_PER_YEAR", 32000)
)
CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR = int(
    os.environ.get("CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR", 100)
)
CHALLENGE_BASE_COST_IN_EURO = int(
    os.environ.get("CHALLENGE_BASE_COST_IN_EURO", 5000)
)

##############################################################################
#
# Storage
#
##############################################################################
DEFAULT_FILE_STORAGE = "grandchallenge.core.storage.PublicS3Storage"

# Subdirectories on root for various files
IMAGE_FILES_SUBDIRECTORY = "images"
EVALUATION_FILES_SUBDIRECTORY = "evaluation"
COMPONENTS_FILES_SUBDIRECTORY = "components"

AWS_S3_FILE_OVERWRITE = False
# Note: deprecated in django storages 2.0
AWS_BUCKET_ACL = "private"
AWS_DEFAULT_ACL = "private"
AWS_S3_MAX_MEMORY_SIZE = 1_048_576  # 100 MB
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")
AWS_S3_URL_PROTOCOL = os.environ.get("AWS_S3_URL_PROTOCOL", "https:")
AWS_S3_OBJECT_PARAMETERS = {
    # Note that these do not affect the Uploads bucket, which is configured separately.
    # See https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.put_object
    "StorageClass": os.environ.get("AWS_S3_DEFAULT_STORAGE_CLASS", "STANDARD")
}
AWS_CLOUDWATCH_REGION_NAME = os.environ.get("AWS_CLOUDWATCH_REGION_NAME")
AWS_CODEBUILD_REGION_NAME = os.environ.get("AWS_CODEBUILD_REGION_NAME")
AWS_SES_REGION_ENDPOINT = f'email.{os.environ.get("AWS_SES_REGION_NAME", AWS_DEFAULT_REGION)}.amazonaws.com'

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

PUBLIC_S3_STORAGE_KWARGS = {
    "bucket_name": os.environ.get(
        "PUBLIC_S3_STORAGE_BUCKET_NAME", "grand-challenge-public"
    ),
    # Public bucket so do not use querystring_auth
    "querystring_auth": False,
    "default_acl": "public-read",
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
    },
    "machina_attachments": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/tmp",
    },
}

ROOT_URLCONF = "config.urls.root"
CHALLENGE_SUBDOMAIN_URL_CONF = "config.urls.challenge_subdomain"
RENDERING_SUBDOMAIN_URL_CONF = "config.urls.rendering_subdomain"

DEFAULT_SCHEME = os.environ.get("DEFAULT_SCHEME", "https")
SITE_SERVER_PORT = os.environ.get("SITE_SERVER_PORT")

# Workaround for https://github.com/ellmetha/django-machina/issues/219
ABSOLUTE_URL_OVERRIDES = {
    "forum.forum": lambda o: reverse(
        "forum:forum", kwargs={"slug": o.slug, "pk": o.pk}
    ),
    "forum_conversation.topic": lambda o: reverse(
        "forum_conversation:topic",
        kwargs={
            "slug": o.slug,
            "pk": o.pk,
            "forum_slug": o.forum.slug,
            "forum_pk": o.forum.pk,
        },
    ),
}

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
# Set the allowed hosts to the cookie domain
ALLOWED_HOSTS = [SESSION_COOKIE_DOMAIN, "web"]

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

IPWARE_META_PRECEDENCE_ORDER = (
    # Set by nginx
    "HTTP_X_FORWARDED_FOR",
    "HTTP_X_REAL_IP",
)

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.environ.get("STATIC_ROOT", "/static/")

STATIC_HOST = os.environ.get("DJANGO_STATIC_HOST", "")
STATIC_URL = f"{STATIC_HOST}/static/"

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",  # for css compression
)

# Vendored static files will be put here
STATICFILES_DIRS = [MACHINA_MAIN_STATIC_DIR]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # Override the machina templates, everything else is found with
            # django.template.loaders.app_directories.Loader
            os.path.join(SITE_ROOT, "grandchallenge/forums/templates/"),
            MACHINA_MAIN_TEMPLATE_DIR,
        ],
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
                "grandchallenge.core.context_processors.help_forum",
                "grandchallenge.core.context_processors.about_page",
                "grandchallenge.core.context_processors.newsletter_signup",
                "grandchallenge.core.context_processors.viewport_names",
                "grandchallenge.core.context_processors.workstation_domains",
                "machina.core.context_processors.metadata",
            ],
            "loaders": default_loaders if DEBUG else cached_loaders,
        },
    }
]

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",  # Keep security at top
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Keep whitenoise after security and before all else
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
    # Django-otp middleware must be after the AuthenticationMiddleware.
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # subdomain_middleware after CurrentSiteMiddleware
    "grandchallenge.subdomains.middleware.subdomain_middleware",
    "grandchallenge.subdomains.middleware.challenge_subdomain_middleware",
    "grandchallenge.subdomains.middleware.subdomain_urlconf_middleware",
    "grandchallenge.timezones.middleware.TimezoneMiddleware",
    "machina.apps.forum_permission.middleware.ForumPermissionMiddleware",
    # 2FA middleware, needs to be after subdomain middleware
    # TwoFactorMiddleware resets the login flow if another page is loaded
    # between login and successfully entering two-factor credentials. We're using
    # a modified version of the original allauth_2fa middleware to pass the
    # correct urlconf.
    "grandchallenge.core.middleware.TwoFactorMiddleware",
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
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",  # Keep whitenoise above staticfiles
    "django.contrib.staticfiles",
    "django.contrib.humanize",
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
    "djcelery_email",  # asynchronous emails
    "guardian",  # per object permissions
    "rest_framework",  # provides REST API
    "knox",  # token auth for REST API
    "crispy_forms",  # bootstrap forms
    "crispy_bootstrap4",
    "django_select2",  # for multiple choice widgets
    "django_summernote",  # for WYSIWYG page editing
    "dal",  # for autocompletion of selection fields
    "dal_select2",  # for autocompletion of selection fields
    "django_extensions",  # custom extensions
    "simple_history",  # for object history
    "corsheaders",  # to allow api communication from subdomains
    "markdownx",  # for editing markdown
    "compressor",  # for compressing css
    "stdimage",
    "django_filters",
    "drf_spectacular",
    "allauth",
    "allauth.account",
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
    # Configure the django-otp package
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    # Enable two-factor auth
    "allauth_2fa",
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
    "grandchallenge.patients",
    "grandchallenge.studies",
    "grandchallenge.registrations",
    "grandchallenge.annotations",
    "grandchallenge.retina_api",
    "grandchallenge.workstations",
    "grandchallenge.workspaces",
    "grandchallenge.reader_studies",
    "grandchallenge.workstation_configs",
    "grandchallenge.policies",
    "grandchallenge.products",
    "grandchallenge.serving",
    "grandchallenge.blogs",
    "grandchallenge.publications",
    "grandchallenge.verifications",
    "grandchallenge.credits",
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
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "django-admin")

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]

GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "GA_TRACKING_ID")

##############################################################################
#
# django-allauth
#
##############################################################################

ACCOUNT_ADAPTER = "grandchallenge.profiles.adapters.AccountAdapter"
ACCOUNT_SIGNUP_FORM_CLASS = "grandchallenge.profiles.forms.SignupForm"

ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN = 30
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
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

# django-allauth-2fa
ALLAUTH_2FA_ALWAYS_REVEAL_BACKUP_TOKENS = False

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
# django-summernote
#
##############################################################################

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
BLEACH_ALLOWED_STYLES = ["height", "margin-left", "text-align", "width"]
BLEACH_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]
BLEACH_STRIP = strtobool(os.environ.get("BLEACH_STRIP", "True"))

# The markdown processor
MARKDOWNX_MEDIA_PATH = datetime.now().strftime("i/%Y/%m/%d/")
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    "markdown.extensions.fenced_code",
    "markdown.extensions.tables",
    "markdown.extensions.sane_lists",
    "markdown.extensions.codehilite",
    "markdown.extensions.attr_list",
    BS4Extension(),
]
MARKDOWNX_MARKDOWNIFY_FUNCTION = (
    "grandchallenge.core.templatetags.bleach.md2html"
)
MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS = {}
MARKDOWNX_IMAGE_MAX_SIZE = {"size": (2000, 0), "quality": 90}
MARKDOWNX_EDITOR_RESIZABLE = "False"

HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"}
}

FORUMS_MIN_ACCOUNT_AGE_DAYS = int(
    os.environ.get("FORUMS_MIN_ACCOUNT_AGE_DAYS", "2")
)
FORUMS_CHALLENGE_CATEGORY_NAME = "Challenges"
MACHINA_BASE_TEMPLATE_NAME = "base.html"
MACHINA_PROFILE_AVATARS_ENABLED = False
MACHINA_FORUM_NAME = "Grand Challenge Forums"
MACHINA_MARKUP_WIDGET = "grandchallenge.core.widgets.MarkdownEditorWidget"
MACHINA_MARKUP_LANGUAGE = (
    "grandchallenge.core.templatetags.bleach.md2html",
    {"link_blank_target": True},
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
    "loggers": {
        "grandchallenge": {
            "level": os.environ.get("GRAND_CHALLENGE_LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": True,
        },
        "django": {
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": True,
        },
        "werkzeug": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        # As AWS_XRAY_CONTEXT_MISSING can only be set to LOG_ERROR,
        # silence errors from this sdk as they flood the logs in
        # RedirectFallbackMiddleware
        "aws_xray_sdk": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": True,
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
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        release=COMMIT_ID,
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")
        ),
        ignore_errors=[PriorStepFailed],
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

REST_KNOX = {"AUTH_HEADER_PREFIX": "Bearer"}

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

###############################################################################
#
# celery
#
###############################################################################

CELERY_TASK_DECORATOR_KWARGS = {
    "acks-late-2xlarge": {
        # For idempotent tasks that take a long time (<7200s)
        # or require a large amount of memory
        "acks_late": True,
        "reject_on_worker_lost": True,
        "queue": "acks-late-2xlarge",
    },
    "acks-late-micro-short": {
        # For idempotent tasks that take a short time (<300s)
        # and do not require a large amount of memory
        "acks_late": True,
        "reject_on_worker_lost": True,
        "queue": "acks-late-micro-short",
    },
}
CELERY_SOLO_QUEUES = {
    *{q["queue"] for q in CELERY_TASK_DECORATOR_KWARGS.values()},
    *{f"{q['queue']}-delay" for q in CELERY_TASK_DECORATOR_KWARGS.values()},
}
ECS_ENABLE_CELERY_SCALE_IN_PROTECTION = strtobool(
    os.environ.get("ECS_ENABLE_CELERY_SCALE_IN_PROTECTION", "False"),
)

CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "django-db")
CELERY_RESULT_PERSISTENT = True
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = timedelta(days=7)
CELERY_TASK_ACKS_LATE = strtobool(
    os.environ.get("CELERY_TASK_ACKS_LATE", "False")
)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(
    os.environ.get("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")
)
CELERY_TASK_SOFT_TIME_LIMIT = int(
    os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "7200")
)
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "7260"))
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": int(1.1 * CELERY_TASK_TIME_LIMIT)
}
CELERY_BROKER_CONNECTION_MAX_RETRIES = 0

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

# Keep results of sent emails
CELERY_EMAIL_CHUNK_SIZE = 1
CELERY_EMAIL_TASK_CONFIG = {"ignore_result": False}

COMPONENTS_DEFAULT_BACKEND = os.environ.get(
    "COMPONENTS_DEFAULT_BACKEND",
    "grandchallenge.components.backends.amazon_sagemaker_batch.AmazonSageMakerBatchExecutor",
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
COMPONENTS_SAGEMAKER_SHIM_ARCH = os.environ.get(
    "COMPONENTS_SAGEMAKER_SHIM_ARCH", "x86_64"
)
COMPONENTS_CREATE_SAGEMAKER_MODEL = strtobool(
    os.environ.get("COMPONENTS_CREATE_SAGEMAKER_MODEL", "False")
)
COMPONENTS_INPUT_BUCKET_NAME = os.environ.get(
    "COMPONENTS_INPUT_BUCKET_NAME", "grand-challenge-components-inputs"
)
COMPONENTS_OUTPUT_BUCKET_NAME = os.environ.get(
    "COMPONENTS_OUTPUT_BUCKET_NAME", "grand-challenge-components-outputs"
)
COMPONENTS_MAXIMUM_IMAGE_SIZE = 10 * GIGABYTE
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
COMPONENTS_CONTAINER_ARCH = os.environ.get(
    "COMPONENTS_CONTAINER_ARCH", "amd64"
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
# workspaces
#
###############################################################################

WORKBENCH_SECRET_KEY = os.environ.get("WORKBENCH_SECRET_KEY")
WORKBENCH_API_URL = os.environ.get("WORKBENCH_API_URL")
WORKBENCH_ADMIN_USERNAME = os.environ.get("WORKBENCH_ADMIN_USERNAME", "demo")

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

CELERY_BEAT_SCHEDULE = {
    "delete_users_who_dont_login": {
        "task": "grandchallenge.profiles.tasks.delete_users_who_dont_login",
        "schedule": crontab(hour=0, minute=0),
    },
    "refresh_expiring_user_tokens": {
        "task": "grandchallenge.github.tasks.refresh_expiring_user_tokens",
        "schedule": crontab(hour=0, minute=15),
    },
    "cleanup_expired_tokens": {
        "task": "grandchallenge.github.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=0, minute=30),
    },
    "ping_google": {
        "task": "grandchallenge.core.tasks.ping_google",
        "schedule": crontab(hour=0, minute=45),
    },
    "clear_sessions": {
        "task": "grandchallenge.core.tasks.clear_sessions",
        "schedule": crontab(hour=1, minute=0),
    },
    "update_publication_metadata": {
        "task": "grandchallenge.publications.tasks.update_publication_metadata",
        "schedule": crontab(hour=1, minute=30),
    },
    "delete_old_user_uploads": {
        "task": "grandchallenge.uploads.tasks.delete_old_user_uploads",
        "schedule": crontab(hour=2, minute=0),
    },
    "remove_inactive_container_images": {
        "task": "grandchallenge.components.tasks.remove_inactive_container_images",
        "schedule": crontab(hour=2, minute=30),
    },
    "update_associated_challenges": {
        "task": "grandchallenge.algorithms.tasks.update_associated_challenges",
        "schedule": crontab(hour=3, minute=0),
    },
    "update_phase_statistics": {
        "task": "grandchallenge.evaluation.tasks.update_phase_statistics",
        "schedule": crontab(hour=3, minute=30),
    },
    "send_unread_notification_emails": {
        "task": "grandchallenge.notifications.tasks.send_unread_notification_emails",
        "schedule": crontab(hour=4, minute=0),
    },
    "update_algorithm_credits": {
        "task": "grandchallenge.algorithms.tasks.set_credits_per_job",
        "schedule": crontab(hour=4, minute=30),
    },
    "update_challenge_cost_statistics": {
        "task": "grandchallenge.challenges.tasks.update_challenge_cost_statistics",
        "schedule": crontab(hour=5, minute=0),
    },
    "update_site_statistics": {
        "task": "grandchallenge.statistics.tasks.update_site_statistics_cache",
        "schedule": crontab(hour=5, minute=30),
    },
    "update_challenge_results_cache": {
        "task": "grandchallenge.challenges.tasks.update_challenge_results_cache",
        "schedule": crontab(minute="*/5"),
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
            "schedule": crontab(minute=f"*/{WORKSTATIONS_GRACE_MINUTES}"),
        }
        for region in WORKSTATIONS_ACTIVE_REGIONS
    },
}

if strtobool(os.environ.get("PUSH_CLOUDWATCH_METRICS", "False")):
    CELERY_BEAT_SCHEDULE["push_metrics_to_cloudwatch"] = {
        "task": "grandchallenge.core.tasks.put_cloudwatch_metrics",
        "schedule": timedelta(seconds=30),
    }

# The name of the group whose members will be able to create algorithms
ALGORITHMS_CREATORS_GROUP_NAME = "algorithm_creators"
# Number of jobs that can be scheduled in one task
ALGORITHMS_JOB_BATCH_LIMIT = int(
    os.environ.get("ALGORITHMS_JOB_BATCH_LIMIT", "32")
)
ALGORITHMS_MAX_ACTIVE_JOBS = int(
    os.environ.get("ALGORITHMS_MAX_ACTIVE_JOBS", "128")
)
# Maximum and minimum values the user can set for algorithm requirements
ALGORITHMS_MIN_MEMORY_GB = 4
ALGORITHMS_MAX_MEMORY_GB = 32
# The SageMaker backend currently has a maximum limit of 3600s
ALGORITHMS_JOB_TIME_LIMIT_SECONDS = os.environ.get(
    "ALGORITHMS_JOB_TIME_LIMIT_SECONDS", "3600"
)
# How many cents per month each user receives by default
ALGORITHMS_USER_CENTS_PER_MONTH = int(
    os.environ.get("ALGORITHMS_USER_CENTS_PER_MONTH", "1000")
)
ALGORITHMS_MAX_DEFAULT_JOBS_PER_MONTH = int(
    os.environ.get("ALGORITHMS_MAX_DEFAULT_JOBS_PER_MONTH", "50")
)
ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE = int(
    os.environ.get("ALGORITHMS_MAX_NUMBER_PER_USER_PER_PHASE", "3")
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
    "evaluation-supplementary",
    "favicon",
    "i",
    "cache",
    "challenge",
    "challenges",
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
    "nudt.edu.cn",
    "ihpc.a-star.edu.sg",
    "raysightmed.com",
    "csu.edu.cn",
    "cerist.dz",
    "ciitvehari.edu.pk",
    "mail.dcu.ie",
    "snu.ac.kr",
    "cau.ac.kr",
    "deepnoid.com",
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

# Maximum file size in bytes to be opened by SimpleITK.ReadImage in cases_tests.utils.get_sitk_image()
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

# Retina specific settings
RETINA_GRADERS_GROUP_NAME = "retina_graders"
RETINA_ADMINS_GROUP_NAME = "retina_admins"


##########################
# JSON SCHEMA
##########################
ALLOWED_JSON_SCHEMA_REF_SRC_REGEXES = (
    "https://vega.github.io/schema/vega-lite/v5.json",
)


##########################
# CONTENT SECURITY POLICY
##########################

CSP_REPORT_ONLY = strtobool(os.environ.get("CSP_REPORT_ONLY", "False"))

CSP_REPORT_URI = os.environ.get("CSP_REPORT_URI")
CSP_REPORT_PERCENTAGE = float(os.environ.get("CSP_REPORT_PERCENTAGE", "0"))

CSP_STATIC_HOST = STATIC_HOST if STATIC_HOST else "'self'"
CSP_MEDIA_HOSTS = (
    (AWS_S3_ENDPOINT_URL,)
    if AWS_S3_ENDPOINT_URL
    else (
        f"https://{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}.s3.amazonaws.com",
        f"https://{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}.s3.{AWS_DEFAULT_REGION}.amazonaws.com",
    )
)

CSP_DEFAULT_SRC = "'none'"
CSP_SCRIPT_SRC = (
    CSP_STATIC_HOST,
    "https://www.googletagmanager.com",  # For Google Analytics
    "https://*.google-analytics.com",  # For Google Analytics
    "'unsafe-eval'",  # Required for vega https://github.com/vega/vega/issues/1106
    "'self'",  # Used in the Django admin
)
CSP_STYLE_SRC = (
    CSP_STATIC_HOST,
    "https://fonts.googleapis.com",
    "'unsafe-inline'",  # TODO fix inline styles
)
CSP_FONT_SRC = (
    CSP_STATIC_HOST,
    "https://fonts.gstatic.com",
)
CSP_IMG_SRC = (
    CSP_STATIC_HOST,
    *CSP_MEDIA_HOSTS,
    "https://www.gravatar.com",  # Used for default mugshots
    "https://www.googletagmanager.com",  # For Google Analytics
    "https://*.google-analytics.com",  # For Google Analytics
    "data:",  # Used by jsoneditor
    "'self'",  # Used by Open Sea Dragon
    "https:",  # Arbitrary files used on blog posts and challenge pages
)
CSP_FRAME_SRC = ("https://mailchi.mp",)  # For products blog posts
CSP_MEDIA_SRC = (
    *CSP_MEDIA_HOSTS,
    "https://user-images.githubusercontent.com",  # Used in blog posts
)
CSP_CONNECT_SRC = (
    "'self'",  # For subdomain leaderboards
    # For workstation subdomain to main
    f"{DEFAULT_SCHEME}://{SESSION_COOKIE_DOMAIN.lstrip('.')}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}",
    # For main to workstation subdomain
    *(
        f"{DEFAULT_SCHEME}://{region}{SESSION_COOKIE_DOMAIN}{f':{SITE_SERVER_PORT}' if SITE_SERVER_PORT else ''}"
        for region in WORKSTATIONS_ACTIVE_REGIONS
    ),
    "https://*.google-analytics.com",  # For Google Analytics
    "https://*.ingest.sentry.io",  # For Sentry errors
)

if STATIC_HOST:
    CSP_CONNECT_SRC += (STATIC_HOST,)  # For the map json

if PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN:
    # Used by Open Sea Dragon and countries json
    CSP_IMG_SRC += (f"https://{PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}",)
    CSP_CONNECT_SRC += (f"https://{PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN}",)

if UPLOADS_S3_USE_ACCELERATE_ENDPOINT:
    CSP_CONNECT_SRC += (
        f"https://{UPLOADS_S3_BUCKET_NAME}.s3-accelerate.amazonaws.com",
    )
else:
    if AWS_S3_ENDPOINT_URL:
        CSP_CONNECT_SRC += (AWS_S3_ENDPOINT_URL,)
    else:
        CSP_CONNECT_SRC += (
            f"https://{UPLOADS_S3_BUCKET_NAME}.s3.{AWS_DEFAULT_REGION}.amazonaws.com",
        )

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    # Allow localhost in development
    CORS_ALLOWED_ORIGIN_REGEXES += [r"^http://localhost:8888$"]

    LOGGING["loggers"]["grandchallenge"]["level"] = "DEBUG"

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
