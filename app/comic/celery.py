import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comic.settings')

app = Celery('comic')

app.config_from_object('django.conf:settings', namespace='CELERY_')

# Load all of the tasks from the registered apps
app.autodiscover_tasks()


@app.task
def cleanup_stale_uploads():
    from evaluation.widgets.uploader import cleanup_stale_files
    cleanup_stale_files()

    import datetime
    with open('/tmp/a', 'ab') as f:
        f.write(datetime.datetime.now().isoformat() + "\n")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        1.0,
        cleanup_stale_uploads.s(),
        name="clean_stale_uploads")
