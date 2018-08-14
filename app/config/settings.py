# Django settings for comic project.
import glob
import os
from datetime import timedelta

import six
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

# Default COMIC settings, to be included by settings.py
# To overwrite these settings local-only, please add a file XX-local.conf.py in the same dir
# and make XX higher then 00

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Django will throw an exeception if the URL you type to load the framework is
# not in the list below. This is a security measure.
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Used as starting points for various other paths. realpath(__file__) starts in
# the "Comic" app dir. We need to  go one dir higher so path.join("..")
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
APPS_DIR = os.path.join(SITE_ROOT, 'grandchallenge')

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'comic',
        'USER': 'comic',
        'PASSWORD': 'secretpassword',
        'HOST': 'postgres',
        'PORT': '5432',
    },
}

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
EMAIL_HOST = ''  # something like smtp.mydomain.com
EMAIL_PORT = 25
DEFAULT_FROM_EMAIL = 'noreply@comicframework.org'

ANONYMOUS_USER_NAME = 'AnonymousUser'
EVERYONE_GROUP_NAME = 'everyone'

AUTH_PROFILE_MODULE = 'profiles.UserProfile'
USERENA_USE_HTTPS = False
USERENA_DEFAULT_PRIVACY = 'open'
LOGIN_URL = '/accounts/signin/'
LOGOUT_URL = '/accounts/signout/'

LOGIN_REDIRECT_URL = '/accounts/login-redirect/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL

# Do not give message popups saying "you have been logged out". Users are expected
# to know they have been logged out when they click the logout button
USERENA_USE_MESSAGES = False,

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

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
MEDIA_ROOT = '/dbox/Dropbox/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/static/'

# Use memcached for caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
    }
}

# In each project there can be a single directory out of which files can be downloaded
# without logging in. In this folder you can put website header images etc.
# for security, only MEDIA_ROOT/<project_name>/COMIC_PUBLIC_FOLDER_NAME are served
# without checking credentials.
COMIC_PUBLIC_FOLDER_NAME = "public_html"

# Transient solution for server content from certain folders publicly. This will be removed
# When a full configurable permissions system is in place, see ticket #244
COMIC_ADDITIONAL_PUBLIC_FOLDER_NAMES = ["results/public", ]

# In each project there can be a single directory from which files can only be
# downloaded by registered members of that project
COMIC_REGISTERED_ONLY_FOLDER_NAME = "datasets"

# All tags that search for results search in the following folder in the project's
# data folder by default
COMIC_RESULTS_FOLDER_NAME = "results"

# the name of the main project: this project is shown when url is loaded without
# arguments, and pages in this project appear as menu items throughout the site
MAIN_PROJECT_NAME = "comic"

# The url for a project in comic is /site/<challenge>. This is quite ugly. It
# would be nicer to be able to use <challenge>.examplehost.com/, like blogger
# does.
# True: Changes links on pages where possible to use subdomain.
SUBDOMAIN_IS_PROJECTNAME = False

# For links to basic comicframework content, for example the main comic help
# page, django needs to know the hostname. This setting is only used when
# SUBDOMAIN_IS_PROJECTNAME = True
MAIN_HOST_NAME = "https://localhost"

# To make logins valid over all subdomains, project1.mydomain, project2.mydomain etc. use
# SESSION_COOKIE_DOMAIN = '.mydomain'
SESSION_COOKIE_DOMAIN = None

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"

# Serve files using django (debug only)
STATIC_URL = '/static/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'd=%^l=xa02an9jn-$!*hy1)5yox$a-$2(ejt-2smimh=j4%8*b'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            str(APPS_DIR),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'grandchallenge.core.contextprocessors.contextprocessors.comic_site',
                'grandchallenge.core.contextprocessors.contextprocessors.subdomain_absolute_uri',
                'grandchallenge.core.contextprocessors.contextprocessors.google_analytics_id',
            ],
        },
    },
]

MIDDLEWARE = (
    # Sentry 404 must be as close as possible to the top
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'grandchallenge.core.middleware.subdomain.SubdomainMiddleware',
    'grandchallenge.core.middleware.project.ProjectMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'config.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'config.wsgi.application'

DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.admin',
]

THIRD_PARTY_APPS = [
    'raven.contrib.django.raven_compat', # error logging
    'djcelery_email', # asynchronous emails
    'django_celery_beat', # periodic tasks
    'userena', # user profiles
    'guardian', # userena dependency, per object permissions
    'easy_thumbnails', # userena dependency
    'social_django', # social authentication with oauth2
    'ckeditor', # WYSIWYG editor, used in granchallenge.pages
    'ckeditor_uploader', # image uploads
    'rest_framework', # provides REST API
    'rest_framework.authtoken', # token auth for REST API
    'crispy_forms', # bootstrap forms
    'favicon', # favicon management
    'django_select2', # for multiple choice widgets
]

LOCAL_APPS = [
    'grandchallenge.admins',
    'grandchallenge.api',
    'grandchallenge.challenges',
    'grandchallenge.core',
    'grandchallenge.evaluation',
    'grandchallenge.jqfileupload',
    'grandchallenge.pages',
    'grandchallenge.participants',
    'grandchallenge.profiles',
    'grandchallenge.teams',
    'grandchallenge.uploads',
    'grandchallenge.cases',
    'grandchallenge.algorithms',
    'grandchallenge.container_exec',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

ADMIN_URL = f'^{os.environ.get("DJANGO_ADMIN_URL", "django-admin")}/'

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'userena.backends.UserenaAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',
                                               '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get(
    'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', '')

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID', 'GA_TRACKING_ID')

# TODO: JM - Add the profile filling as a partial
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'grandchallenge.profiles.social_auth.pipeline.profile.create_profile',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Do not sanitize redirects for social auth so we can redirect back to
# other subdomains
SOCIAL_AUTH_SANITIZE_REDIRECTS = False

# Django 1.6 introduced a new test runner, use it
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# buttons for WYSIWYG editor in page admin
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': [
            [
                'Source',
                '-', 'Undo', 'Redo',
                '-', 'Bold', 'Italic', 'Underline', 'Format',
                '-', 'Link', 'Unlink', 'Anchor',
                '-', 'Table', 'BulletedList', 'NumberedList', 'Image',
                'SpecialChar',
                '-', 'Maximize',

            ]
        ],
        'width': 840,
        'height': 300,
        'toolbarCanCollapse': False,
        'entities': False,
        'extraAllowedContent': '*(*)', # Allows any class in ckeditor html
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
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
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR', # To capture more than ERROR, change to WARNING, INFO, etc.
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

RAVEN_CONFIG = {
    'dsn': os.environ.get('DJANGO_SENTRY_DSN', ''),
}

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_SOFT_TIME_LIMIT = 7200
CELERY_TASK_TIME_LIMIT = 7260

CONTAINER_EXEC_DOCKER_BASE_URL = 'unix://var/run/docker.sock'
CONTAINER_EXEC_MEMORY_LIMIT = "4g"
CONTAINER_EXEC_IO_IMAGE = "alpine:3.8"
CONTAINER_EXEC_CPU_QUOTA = 100000
CONTAINER_EXEC_CPU_PERIOD = 100000

CELERY_BEAT_SCHEDULE = {
    'cleanup_stale_uploads': {
        'task': 'grandchallenge.jqfileupload.tasks.cleanup_stale_uploads',
        'schedule': timedelta(hours=1),
    },
    'clear_sessions': {
        'task': 'grandchallenge.container_exec.tasks.clear_sessions',
        'schedule': timedelta(days=1),
    },
}

CELERY_TASK_ROUTES = {
    'grandchallenge.container_exec.tasks.execute_job': 'evaluation',
}

# Set which template pack to use for forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# When using bootstrap error messages need to be renamed to danger
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

JQFILEUPLOAD_UPLOAD_SUBIDRECTORY = "jqfileupload"

# Get *.conf from the directory this file is in and execute these in order.
# To include your own local settings, put these in a  a 'XX-local.conf' file in the
# current dir. XX should be a number which determines the order of execution. 
# Executed last overwrites previous settings.  

path = os.path.join(os.path.dirname(__file__), 'settings', '*.conf')
conf_files = glob.glob(path)

if len(conf_files) == 0:
    msg = "Could not find any files matching '" + path + "'. There should be at least one configuration file containing django settings at that location."
    raise ImproperlyConfigured(msg)

conf_files.sort()
for conf_file in conf_files:
    with open(conf_file) as f:
        code = compile(f.read(), conf_file, 'exec')
        six.exec_(code)

CKEDITOR_UPLOAD_PATH = 'uploads/'

if MEDIA_ROOT[-1] != "/":
    msg = "MEDIA_ROOT setting should end in a slash. Found '" + MEDIA_ROOT + "'. Please add a slash"
    raise ImproperlyConfigured(msg)

if MAIN_HOST_NAME[-1] == '/':
    raise ImproperlyConfigured("MAIN_HOST_NAME should end without a slash")

ENABLE_DEBUG_TOOLBAR = False

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

    if ENABLE_DEBUG_TOOLBAR:
        INSTALLED_APPS += (
            'debug_toolbar',
        )

        MIDDLEWARE += (
            'debug_toolbar.middleware.DebugToolbarMiddleware',
        )

        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': 'config.toolbar_callback',
        }
