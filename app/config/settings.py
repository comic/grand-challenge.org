import os
import re
from datetime import datetime, timedelta
from distutils.util import strtobool as strtobool_i
from itertools import product
from urllib.parse import quote

import sentry_sdk
from corsheaders.defaults import default_headers
from disposable_email_domains import blocklist
from django.contrib.messages import constants as messages
from django.urls import reverse
from machina import MACHINA_MAIN_STATIC_DIR, MACHINA_MAIN_TEMPLATE_DIR
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from config.denylist import USERNAME_DENYLIST
from grandchallenge.core.utils.markdown import BS4Extension


def strtobool(val) -> bool:
    """Return disutils.util.strtobool as a boolean."""
    return bool(strtobool_i(val))


DEBUG = strtobool(os.environ.get("DEBUG", "True"))

ATOMIC_REQUESTS = strtobool(os.environ.get("ATOMIC_REQUESTS", "True"))

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
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
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
COMPONENTS_FILES_SUBDIRECTORY = "components"

AWS_S3_FILE_OVERWRITE = False
# Note: deprecated in django storages 2.0
AWS_BUCKET_ACL = "private"
AWS_DEFAULT_ACL = "private"
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", None)

# This is for storing files that should not be served to the public
PRIVATE_S3_STORAGE_KWARGS = {
    "access_key": os.environ.get("PRIVATE_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PRIVATE_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PRIVATE_S3_STORAGE_BUCKET_NAME", "grand-challenge-private"
    ),
    "endpoint_url": os.environ.get("PRIVATE_S3_STORAGE_ENDPOINT_URL", None),
}

PROTECTED_S3_STORAGE_KWARGS = {
    "access_key": os.environ.get("PROTECTED_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PROTECTED_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PROTECTED_S3_STORAGE_BUCKET_NAME", "grand-challenge-protected"
    ),
    "endpoint_url": os.environ.get("PROTECTED_S3_STORAGE_ENDPOINT_URL", None),
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
    "access_key": os.environ.get("PUBLIC_S3_STORAGE_ACCESS_KEY", ""),
    "secret_key": os.environ.get("PUBLIC_S3_STORAGE_SECRET_KEY", ""),
    "bucket_name": os.environ.get(
        "PUBLIC_S3_STORAGE_BUCKET_NAME", "grand-challenge-public"
    ),
    # Public bucket so do not use querystring_auth
    "querystring_auth": False,
    "default_acl": "public-read",
}

# Key pair used for signing CloudFront URLS, only used if
# PROTECTED_S3_STORAGE_USE_CLOUDFRONT is True
CLOUDFRONT_KEY_PAIR_ID = os.environ.get("CLOUDFRONT_KEY_PAIR_ID", "")
CLOUDFRONT_PRIVATE_KEY_PATH = os.environ.get("CLOUDFRONT_PRIVATE_KEY_PATH", "")
CLOUDFRONT_URL_EXPIRY_SECONDS = int(
    os.environ.get("CLOUDFRONT_URL_EXPIRY_SECONDS", "300")  # 5 mins
)

##############################################################################
#
# Caching
#
##############################################################################

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
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

# Workaround for https://github.com/ellmetha/django-machina/issues/219
ABSOLUTE_URL_OVERRIDES = {
    "forum.forum": lambda o: reverse(
        "forum:forum", kwargs={"slug": o.slug, "pk": o.pk},
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
# We're always running behind a proxy so set these to true
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Trust all subdomains for CSRF, used for jqfileupload. Changed the name
# of the CSRF token as existing ones are already in use.
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN
CSRF_COOKIE_NAME = "_csrftoken"
CSRF_TRUSTED_ORIGINS = [
    SESSION_COOKIE_DOMAIN,
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
X_FRAME_OPTIONS = os.environ.get("X_FRAME_OPTIONS", "DENY")
# "origin-when-cross-origin" required for jqfileupload for cross domain POSTs
SECURE_REFERRER_POLICY = os.environ.get(
    "SECURE_REFERRER_POLICY", "origin-when-cross-origin"
)

IPWARE_META_PRECEDENCE_ORDER = (
    # Set by nginx
    "HTTP_X_FORWARDED_FOR",
    "HTTP_X_REAL_IP",
)

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
STATICFILES_DIRS = ["/opt/static/", MACHINA_MAIN_STATIC_DIR]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "d=%^l=xa02an9jn-$!*hy1)5yox$a-$2(ejt-2smimh=j4%8*b"
)

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
                "machina.core.context_processors.metadata",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
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
    "machina.apps.forum_permission.middleware.ForumPermissionMiddleware",
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
]

THIRD_PARTY_APPS = [
    "django_celery_results",  # database results backend
    "django_celery_beat",  # periodic tasks
    "djcelery_email",  # asynchronous emails
    "guardian",  # per object permissions
    "easy_thumbnails",  # for mugshots
    "rest_framework",  # provides REST API
    "knox",  # token auth for REST API
    "crispy_forms",  # bootstrap forms
    "django_select2",  # for multiple choice widgets
    "django_summernote",  # for WYSIWYG page editing
    "dal",  # for autocompletion of selection fields
    "dal_select2",  # for autocompletion of selection fields
    "django_extensions",  # custom extensions
    "simple_history",  # for object history
    "corsheaders",  # to allow api communication from subdomains
    "markdownx",  # for editing markdown
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
]

LOCAL_APPS = [
    "grandchallenge.admins",
    "grandchallenge.anatomy",
    "grandchallenge.api",
    "grandchallenge.api_tokens",
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
    "grandchallenge.components",
    "grandchallenge.statistics",
    "grandchallenge.archives",
    "grandchallenge.patients",
    "grandchallenge.studies",
    "grandchallenge.registrations",
    "grandchallenge.annotations",
    "grandchallenge.retina_core",
    "grandchallenge.retina_importers",
    "grandchallenge.retina_api",
    "grandchallenge.workstations",
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
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = f'{os.environ.get("DJANGO_ADMIN_URL", "django-admin")}/'

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "GA_TRACKING_ID")

##############################################################################
#
# django-allauth
#
##############################################################################

ACCOUNT_ADAPTER = "grandchallenge.profiles.adapters.AccountAdapter"
ACCOUNT_SIGNUP_FORM_CLASS = "grandchallenge.profiles.forms.SignupForm"

ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USERNAME_MIN_LENGTH = 4
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USERNAME_BLACKLIST = USERNAME_DENYLIST

SOCIALACCOUNT_ADAPTER = "grandchallenge.profiles.adapters.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "gmail": {
        "APP": {
            "client_id": os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", ""),
            "secret": os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", ""),
        }
    }
}

# Use full paths as view name lookups do not work on subdomains
LOGIN_URL = "/accounts/login/"
LOGOUT_URL = "/accounts/logout/"
LOGIN_REDIRECT_URL = "/users/profile/"

PROFILES_MUGSHOT_SIZE = 460

##############################################################################
#
# actstream
#
##############################################################################

ACTSTREAM_ENABLE = strtobool(os.environ.get("ACTSTREAM_ENABLE", "True"))
ACTSTREAM_SETTINGS = {
    "MANAGER": "grandchallenge.notifications.managers.ActionManager",
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
    "a": ["href", "title", "target", "rel"],
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
    BS4Extension(),
]
MARKDOWNX_MARKDOWNIFY_FUNCTION = (
    "grandchallenge.core.templatetags.bleach.md2html"
)
MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS = {}
MARKDOWNX_IMAGE_MAX_SIZE = {"size": (2000, 0), "quality": 90}

HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"},
}

FORUMS_CHALLENGE_CATEGORY_NAME = "Challenges"
MACHINA_BASE_TEMPLATE_NAME = "base.html"
MACHINA_PROFILE_AVATARS_ENABLED = False
MACHINA_FORUM_NAME = "Grand Challenge Forums"

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
WORKSTATION_SENTRY_DSN = os.environ.get("WORKSTATION_SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        release=COMMIT_ID,
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.01")
        ),
    )
    ignore_logger("django.security.DisallowedHost")

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
}

REST_KNOX = {
    "AUTH_HEADER_PREFIX": "Bearer",
}

###############################################################################
#
# CORS
#
###############################################################################

VALID_SUBDOMAIN_REGEX = r"[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?"
CORS_ORIGIN_REGEX_WHITELIST = [
    rf"^https:\/\/{VALID_SUBDOMAIN_REGEX}{re.escape(SESSION_COOKIE_DOMAIN)}$",
    rf"^https:\/\/{VALID_SUBDOMAIN_REGEX}.static.observableusercontent.com$",
]
CORS_ALLOW_HEADERS = [
    *default_headers,
    "content-range",
    "content-disposition",
    "content-description",
]
# SESSION_COOKIE_SAMESITE should be set to "lax" so won't send credentials
# across domains, but this will allow workstations to access the api
CORS_ALLOW_CREDENTIALS = True

###############################################################################
#
# celery
#
###############################################################################

CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "django-db")
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_ACKS_LATE = strtobool(
    os.environ.get("CELERY_TASK_ACKS_LATE", "False")
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
    celery_access_key = quote(os.environ.get("BROKER_AWS_ACCESS_KEY"), safe="")
    celery_secret_key = quote(os.environ.get("BROKER_AWS_SECRET_KEY"), safe="")
    CELERY_BROKER_URL = f"sqs://{celery_access_key}:{celery_secret_key}@"

    CELERY_WORKER_ENABLE_REMOTE_CONTROL = False
    CELERY_BROKER_USE_SSL = True

    CELERY_BROKER_TRANSPORT_OPTIONS.update(
        {
            "queue_name_prefix": os.environ.get(
                "CELERY_BROKER_QUEUE_NAME_PREFIX", "gclocalhost-"
            ),
            "region": os.environ.get("CELERY_BROKER_REGION", "eu-central-1"),
            "polling_interval": int(
                os.environ.get("CELERY_BROKER_POLLING_INTERVAL", "1")
            ),
        }
    )
else:
    CELERY_BROKER_URL = os.environ.get("BROKER_URL", "redis://redis:6379/0")

COMPONENTS_DOCKER_BASE_URL = os.environ.get(
    "COMPONENTS_DOCKER_BASE_URL", "unix://var/run/docker.sock"
)
COMPONENTS_DOCKER_TLSVERIFY = strtobool(
    os.environ.get("COMPONENTS_DOCKER_TLSVERIFY", "False")
)
COMPONENTS_DOCKER_TLSCACERT = os.environ.get("COMPONENTS_DOCKER_TLSCACERT", "")
COMPONENTS_DOCKER_TLSCERT = os.environ.get("COMPONENTS_DOCKER_TLSCERT", "")
COMPONENTS_DOCKER_TLSKEY = os.environ.get("COMPONENTS_DOCKER_TLSKEY", "")
COMPONENTS_MEMORY_LIMIT = os.environ.get("COMPONENTS_MEMORY_LIMIT", "4g")
COMPONENTS_IO_IMAGE = "alpine:3.12"
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
WORKSTATIONS_ALGORITHM_JOB_QUERY_PARAM = "algorithmJob"
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
WORKSTATION_INTERNAL_NETWORK = strtobool(
    os.environ.get("WORKSTATION_INTERNAL_NETWORK", "False")
)
# Which regions are available for workstations to run in
WORKSTATIONS_ACTIVE_REGIONS = os.environ.get(
    "WORKSTATIONS_ACTIVE_REGIONS", "eu-central-1"
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

CELERY_BEAT_SCHEDULE = {
    "ping_google": {
        "task": "grandchallenge.core.tasks.ping_google",
        "schedule": timedelta(days=1),
    },
    "update_publication_metadata": {
        "task": "grandchallenge.publications.tasks.update_publication_metadata",
        "schedule": timedelta(days=1),
    },
    "cleanup_stale_uploads": {
        "task": "grandchallenge.jqfileupload.tasks.cleanup_stale_uploads",
        "schedule": timedelta(hours=1),
    },
    "clear_sessions": {
        "task": "grandchallenge.core.tasks.clear_sessions",
        "schedule": timedelta(days=1),
    },
    "update_challenge_results_cache": {
        "task": "grandchallenge.challenges.tasks.update_challenge_results_cache",
        "schedule": timedelta(minutes=5),
    },
    "validate_external_challenges": {
        "task": "grandchallenge.challenges.tasks.check_external_challenge_urls",
        "schedule": timedelta(days=1),
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
    # Cleanup evaluation jobs on the evaluation queue
    "mark_long_running_evaluation_jobs_failed": {
        "task": "grandchallenge.components.tasks.mark_long_running_jobs_failed",
        "kwargs": {"app_label": "evaluation", "model_name": "evaluation"},
        "options": {"queue": "evaluation"},
        "schedule": timedelta(hours=1),
    },
    "mark_long_running_algorithm_gpu_jobs_failed": {
        "task": "grandchallenge.components.tasks.mark_long_running_jobs_failed",
        "kwargs": {
            "app_label": "algorithms",
            "model_name": "job",
            "extra_filters": {"algorithm_image__requires_gpu": True},
        },
        "options": {"queue": "gpu"},
        "schedule": timedelta(hours=1),
    },
    "mark_long_running_algorithm_jobs_failed": {
        "task": "grandchallenge.components.tasks.mark_long_running_jobs_failed",
        "kwargs": {
            "app_label": "algorithms",
            "model_name": "job",
            "extra_filters": {"algorithm_image__requires_gpu": False},
        },
        "options": {"queue": "evaluation"},
        "schedule": timedelta(hours=1),
    },
}

CELERY_TASK_ROUTES = {
    "grandchallenge.components.tasks.execute_job": "evaluation",
    "grandchallenge.components.tasks.validate_docker_image": "images",
    "grandchallenge.cases.tasks.build_images": "images",
}

# The name of the group whose members will be able to create algorithms
ALGORITHMS_CREATORS_GROUP_NAME = "algorithm_creators"

# The name of the group whose uploaded dicom files will be retained if the image builder fails
DICOM_DATA_CREATORS_GROUP_NAME = "dicom_creators"

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
    JQFILEUPLOAD_UPLOAD_SUBIDRECTORY,
    *USERNAME_DENYLIST,
    *WORKSTATIONS_RENDERING_SUBDOMAINS,
}

# Disallow registration from certain domains
DISALLOWED_EMAIL_DOMAINS = {
    "qq.com",
    "gm.uit.edu.vn",
    *blocklist,
}

# Modality name constants
MODALITY_OCT = "OCT"  # Optical coherence tomography
MODALITY_CF = "Fundus Photography"  # Color fundus photography
MODALITY_FA = "Flurescein Angiography"  # Fluorescein angiography
MODALITY_IR = "Infrared Reflectance Imaging"  # Infrared Reflectance imaging

# Maximum file size in bytes to be opened by SimpleITK.ReadImage in cases.models.Image.get_sitk_image()
MAX_SITK_FILE_SIZE = 268_435_456  # 256 mb

# The maximum size of all the files in an upload session in bytes
UPLOAD_SESSION_MAX_BYTES = 10_737_418_240  # 10 gb

# Some forms have a lot of data, such as a reader study update view
# that can contain reports about the medical images
DATA_UPLOAD_MAX_MEMORY_SIZE = 16_777_216  # 16 mb

# Default maximum width or height for thumbnails in retina workstation
RETINA_DEFAULT_THUMBNAIL_SIZE = 128

# Retina specific settings
RETINA_GRADERS_GROUP_NAME = "retina_graders"
RETINA_ADMINS_GROUP_NAME = "retina_admins"
RETINA_IMPORT_USER_NAME = "retina_import_user"

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

    # Allow localhost in development
    CORS_ORIGIN_REGEX_WHITELIST += [r"^http://localhost:8888$"]

    LOGGING["loggers"]["grandchallenge"]["level"] = "DEBUG"

    PUBLIC_S3_STORAGE_KWARGS.update(
        {
            "custom_domain": f"localhost:9000/{PUBLIC_S3_STORAGE_KWARGS['bucket_name']}",
            "secure_urls": False,
            "endpoint_url": "http://minio-public:9000",
        }
    )
    DEMO_ALGORITHM_IMAGE_PATH = os.path.join(SITE_ROOT, "algorithm.tar.gz")

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
