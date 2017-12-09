# Django settings for comic project.
import glob
import os
from datetime import timedelta

import six
from celery.schedules import crontab
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

# Default COMIC settings, to be included by settings.py
# To overwrite these settings local-only, please add a file XX-local.conf.py in the same dir
# and make XX higher then 00

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Django will throw an exeception if the URL you type to load the framework is
# not in the list below. This is a security measure.
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Used as starting points for various other paths. realpath(__file__) starts in
# the "Comic" app dir. We need to  go one dir higher so path.join("..")
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'comic',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'db',
        'PORT': '3306',
    }
}

# console.EmailBackend will print all emails to console, which is useful in development.
# For actually sending emails, set EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = ''  # something like smtp.mydomain.com
EMAIL_PORT = 25
DEFAULT_FROM_EMAIL = 'noreply@comicframework.org'

ANONYMOUS_USER_NAME = 'AnonymousUser'
EVERYONE_GROUP_NAME = 'everyone'

AUTH_PROFILE_MODULE = 'profiles.UserProfile'
USERENA_USE_HTTPS = False
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
# TIME_ZONE = 'America/Chicago'
TIME_ZONE = None

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

# root synched folder for dropbox. Tags like include_file read from this.
# Should contain a folder for each project, e.g. /VESSEL12 /ANODE09
DROPBOX_ROOT = MEDIA_ROOT

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

# An overview can be rendered of all projects in the framework. In addition,
# external projects can be included from the file below. Relative to
# DROPBOX_ROOT + MAIN_PROJECT_NAME
EXTERNAL_PROJECTS_FILE = "challengestats.xls"

# Each project in ALL_PROJECTS_FILE can have a 100x100 image thumbnail associated
# with it. Thumbnail images are looked for in the folder below. Filenames should
# <project_abbreviation>.jpg. For example, If a projects value in the "abreviation"
# column 'ABC2013' then the framework will include the image 'ABD2013.png' from the
# directory below. Directory is relative to DROPBOX_ROOT+MAIN_PROJECT_NAME
EXTERNAL_PROJECTS_IMAGE_FOLDER = "public_html/images/all_challenges/"

# The url for a project in comic is /site/<projectname>. This is quite ugly. It
# would be nicer to be able to use <projectname>.examplehost.com/, like blogger
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

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    SITE_ROOT + "/" + "static",
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'd=%^l=xa02an9jn-$!*hy1)5yox$a-$2(ejt-2smimh=j4%8*b'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.filesystem.Loader',

    #     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'comicsite.contextprocessors.contextprocessors.comic_site',
    'comicsite.contextprocessors.contextprocessors.subdomain_absolute_uri'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'comicsite.middleware.subdomain.SubdomainMiddleware',
    'comicsite.middleware.project.ProjectMiddleware',
    # 'comicsite.middleware.customhostnames.CustomHostnamesMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Rollbar needs to be last
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
)

ROOT_URLCONF = 'comic.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'comic.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    # FIXME: Path to template path. This might be temporary.
    # At the moment some of the admin templates are overloaded here. I think the comicsite app is a better place to do that.
    os.path.normpath(os.path.dirname(__file__) + '/templates'),

)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Needed for userena
    'django.contrib.sites',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    # all objects used in the framework, e.g. algorithm, dataset, team, result.
    'comicmodels',
    # comicsite is the where main web portal of this framework lives
    'comicsite',
    # placed admin below comicsite to be able to override standard admin templates
    'django.contrib.admin',
    # profiles extends userena and gives functionality to manage user profiles
    # profiles needs to be loaded before userena
    'profiles',
    # userena provides advanced user management
    'userena',
    # guardian (depency of userena) implements advanced authentication on a per object basis
    'guardian',
    # easy-thumbnails (depency of userena) is a thumbnailing application
    'easy_thumbnails',
    # social-auth provides authentication via social accounts using openid and oauth2
    'social_django',
    # provides abstraction layer for file upload/download
    'filetransfers',
    # html WYSIWYG editor
    'ckeditor',
    # automated evaluation
    'evaluation',
    'jqfileupload',
    'rest_framework',
    'rest_framework.authtoken',
    'api',
    # bootstrap forms
    'crispy_forms',
)

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

# TODO: JM - Add the profile filling as a partial
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'profiles.social_auth.pipeline.profile.create_profile',
    'profiles.social_auth.pipeline.profile.set_project_permissions',
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
    }
}


# A sample logging configuration. More info in configuration can be found at
# https://docs.djangoproject.com/en/dev/topics/logging/ .
# This configuration writes WARNING and worse errors to an error log file, and
# sends an email to all admins. It also writes INFO logmessages and worse to a
# regular log file.
LOG_FILEPATH = "django.log"
LOG_FILEPATH_ERROR = "django_error.log"
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'level': 'WARNING'
        },
        'write_to_logfile': {
            'class': 'logging.FileHandler',
            'filename': LOG_FILEPATH,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'write_to_error_logfile': {
            'class': 'logging.FileHandler',
            'filename': LOG_FILEPATH_ERROR,
            'formatter': 'verbose',
            'level': 'WARNING'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['mail_admins', 'write_to_logfile',
                         'write_to_error_logfile'],
            'propagate': True,
            'level': 'INFO',
        },

    }
}

# Rollbar Configuration
ROLLBAR = {
    'access_token': os.environ.get('ROLLBAR_ACCESS_TOKEN', ''),
    'environment': 'development' if DEBUG else 'production',
    'branch': 'master',
    'root': os.path.abspath(os.getcwd()),
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

CELERY_BROKER_URL = 'amqp://rabbitmq'
CELERY_RESULT_BACKEND = 'amqp://rabbitmq'
CELERY_TASK_SOFT_TIME_LIMIT = 3600
CELERY_TASK_TIME_LIMIT = 3660

DOCKER_BASE_URL = 'unix://var/run/docker.sock'

CELERY_BEAT_SCHEDULE = {
    'cleanup_stale_uploads': {
        'task': 'jqfileupload.tasks.cleanup_stale_uploads',
        'schedule': timedelta(seconds=60),
    }
}

# Set which template pack to use for forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# When using bootstrap error messages need to be renamed to danger
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

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

CKEDITOR_UPLOAD_PATH = MEDIA_ROOT

if MEDIA_ROOT[-1] != "/":
    msg = "MEDIA_ROOT setting should end in a slash. Found '" + MEDIA_ROOT + "'. Please add a slash"
    raise ImproperlyConfigured(msg)

if DROPBOX_ROOT[-1] != "/":
    msg = "DROPBOX_ROOT setting should end in a slash. Found '" + DROPBOX_ROOT + "'. Please add a slash"
    raise ImproperlyConfigured(msg)

if MAIN_HOST_NAME[-1] == '/':
    raise ImproperlyConfigured("MAIN_HOST_NAME should end without a slash")

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
