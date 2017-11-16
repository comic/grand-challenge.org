# Django settings for comic project.
import glob
import os
from datetime import timedelta

import six
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

# These need to be set in the conf files
MEDIA_ROOT = ''
DROPBOX_ROOT = ''

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

CELERY_BEAT_SCHEDULE = {
    'cleanup_stale_uploads': {
        'task': 'evaluation.tasks.cleanup_stale_uploads',
        'schedule': timedelta(seconds=60),
    }
}

if MEDIA_ROOT[-1] != "/":
    msg = "MEDIA_ROOT setting should end in a slash. Found '" + MEDIA_ROOT + "'. Please add a slash"
    raise ImproperlyConfigured(msg)

if DROPBOX_ROOT[-1] != "/":
    msg = "DROPBOX_ROOT setting should end in a slash. Found '" + DROPBOX_ROOT + "'. Please add a slash"
    raise ImproperlyConfigured(msg)
