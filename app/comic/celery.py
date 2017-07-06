import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comic.settings')

app = Celery('comic')

app.config_from_object('django.conf:settings', namespace='CELERY_')

# Load all of the tasks from the registered apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
