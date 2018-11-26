# Django settings for comic project.
import glob
import os
import re
import uuid
from datetime import timedelta
from distutils.util import strtobool as strtobool_i

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured


def strtobool(val) -> bool:
    """ Returns disutils.util.strtobool as a boolean """
    return bool(strtobool_i(val))


# Default COMIC settings, to be included by settings.py
DEBUG = strtobool(os.environ.get("DEBUG", "True"))

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Who gets the 404 notifications?
manager_email = os.environ.get("MANAGER_EMAIL", None)
if manager_email:
    MANAGERS = [("Manager", manager_email)]

IGNORABLE_404_URLS = [
    re.compile(r"\.(php|cgi|asp)/"),
    re.compile(r"^/phpmyadmin/"),
]

# Django will throw an exeception if the URL you type to load the framework is
# not in the list below. This is a security measure.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web"]

# Used as starting points for various other paths. realpath(__file__) starts in
# the "Comic" app dir. We need to  go one dir higher so path.join("..")
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
APPS_DIR = os.path.join(SITE_ROOT, "grandchallenge")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
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

# In each project there can be a single directory out of which files can be downloaded
# without logging in. In this folder you can put website header images etc.
# for security, only MEDIA_ROOT/<project_name>/COMIC_PUBLIC_FOLDER_NAME are served
# without checking credentials.
COMIC_PUBLIC_FOLDER_NAME = "public_html"

# Transient solution for server content from certain folders publicly. This will be removed
# When a full configurable permissions system is in place, see ticket #244
COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES = ["results/public"]

# In each project there can be a single directory from which files can only be
# downloaded by registered members of that project
COMIC_REGISTERED_ONLY_FOLDER_NAME = "datasets"

# the name of the main project: this project is shown when url is loaded without
# arguments, and pages in this project appear as menu items throughout the site
MAIN_PROJECT_NAME = os.environ.get("MAIN_PROJECT_NAME", "comic")

# The url for a project in comic is /site/<challenge>. This is quite ugly. It
# would be nicer to be able to use <challenge>.examplehost.com/, like blogger
# does.
# True: Changes links on pages where possible to use subdomain.
SUBDOMAIN_IS_PROJECTNAME = strtobool(
    os.environ.get("SUBDOMAIN_IS_PROJECTNAME", "False")
)

# For links to basic comicframework content, for example the main comic help
# page, django needs to know the hostname. This setting is only used when
# SUBDOMAIN_IS_PROJECTNAME = True
MAIN_HOST_NAME = os.environ.get("MAIN_HOST_NAME", "https://localhost")

# To make logins valid over all subdomains, project1.mydomain, project2.mydomain etc. use
# SESSION_COOKIE_DOMAIN = '.mydomain'
SESSION_COOKIE_DOMAIN = os.environ.get("SESSION_COOKIE_DOMAIN", None)
SESSION_COOKIE_SECURE = strtobool(
    os.environ.get("SESSION_COOKIE_SECURE", "False")
)
CSRF_COOKIE_SECURE = strtobool(os.environ.get("CSRF_COOKIE_SECURE", "False"))

# Set the allowed hosts to the cookie domain
if SESSION_COOKIE_DOMAIN:
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

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"

# Serve files using django (debug only)
STATIC_URL = "/static/"

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_STORAGE = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)

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
                "grandchallenge.core.contextprocessors.contextprocessors.comic_site",
                "grandchallenge.core.contextprocessors.contextprocessors.subdomain_absolute_uri",
                "grandchallenge.core.contextprocessors.contextprocessors.google_analytics_id",
            ]
        },
    }
]

MIDDLEWARE = (
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    # Keep BrokenLinkEmailsMiddleware near the top
    "raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "grandchallenge.core.middleware.subdomain.SubdomainMiddleware",
    "grandchallenge.core.middleware.project.ProjectMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "config.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "config.wsgi.application"

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "raven.contrib.django.raven_compat",  # error logging
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
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = f'{os.environ.get("DJANGO_ADMIN_URL", "django-admin")}/'

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "userena.backends.UserenaAuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get(
    "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", ""
)
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get(
    "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", ""
)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_ANALYTICS_ID = os.environ.get("GOOGLE_ANALYTICS_ID", "GA_TRACKING_ID")

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
    "iframe",  # Allowed for now for continuous registration challenge
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
    "div": ["data-geochart"],  # Required for geocharts
    "iframe": ["src", "sandbox"],  # For continuous registration challenge
    "img": ["height", "src", "width"],
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

RAVEN_CONFIG = {"dsn": os.environ.get("DJANGO_SENTRY_DSN", "")}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAdminUser",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
}

CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_SOFT_TIME_LIMIT = 7200
CELERY_TASK_TIME_LIMIT = 7260
CELERY_TASK_ALWAYS_EAGER = strtobool(os.environ.get("CELERY_TASK_ALWAYS_EAGER", "False"))

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
CONTAINER_EXEC_MEMORY_LIMIT = "4g"
CONTAINER_EXEC_IO_IMAGE = "alpine:3.8"
CONTAINER_EXEC_IO_SHA256 = (
    "sha256:196d12cf6ab19273823e700516e98eb1910b03b17840f9d5509f03858484d321"
)
CONTAINER_EXEC_CPU_QUOTA = 100000
CONTAINER_EXEC_CPU_PERIOD = 100000

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
}

CELERY_TASK_ROUTES = {
    "grandchallenge.container_exec.tasks.execute_job": "evaluation"
}

# Set which template pack to use for forms
CRISPY_TEMPLATE_PACK = "bootstrap4"

# When using bootstrap error messages need to be renamed to danger
MESSAGE_TAGS = {messages.ERROR: "danger"}

JQFILEUPLOAD_UPLOAD_SUBIDRECTORY = "jqfileupload"

# CIRRUS Is an external application that can view images
CIRRUS_APPLICATION = "https://apps.diagnijmegen.nl/Applications/CIRRUSWeb_master_98d13770/#!/?workstation=BasicWorkstation"
CIRRUS_BASE_IMAGE_QUERY_PARAM = "grand_challenge_image"
CIRRUS_ANNOATION_QUERY_PARAM = "grand_challenge_overlay"

# Disallow some challenge names due to subdomain or media folder clashes
DISALLOWED_CHALLENGE_NAMES = [
    "www",
    "m",
    "mx",
    "mobile",
    "mail",
    "webmail",
    "images",
    "logos",
    "banners",
    "mugshots",
    "docker",
    "evaluation",
    "evaluation-supplementary",
    "favicon",
    "i",
    JQFILEUPLOAD_UPLOAD_SUBIDRECTORY,
]

if MEDIA_ROOT[-1] != "/":
    msg = (
        "MEDIA_ROOT setting should end in a slash. Found '"
        + MEDIA_ROOT
        + "'. Please add a slash"
    )
    raise ImproperlyConfigured(msg)

if MAIN_HOST_NAME[-1] == "/":
    raise ImproperlyConfigured("MAIN_HOST_NAME should end without a slash")

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

    if ENABLE_DEBUG_TOOLBAR:
        INSTALLED_APPS += ("debug_toolbar",)

        MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

        DEBUG_TOOLBAR_CONFIG = {
            "SHOW_TOOLBAR_CALLBACK": "config.toolbar_callback"
        }

if not COMIC_PUBLIC_FOLDER_NAME:
    raise ImproperlyConfigured(
        "Don't know from which folder serving publiv files"
        "is allowed. Please add a setting like "
        '\'COMIC_PUBLIC_FOLDER_NAME = "public_html"'
        " to your .conf file."
    )

if not COMIC_REGISTERED_ONLY_FOLDER_NAME:
    raise ImproperlyConfigured(
        "Don't know from which folder serving protected files"
        "is allowed. Please add a setting like "
        '\'COMIC_REGISTERED_ONLY_FOLDER_NAME = "datasets"'
        " to your .conf file."
    )
