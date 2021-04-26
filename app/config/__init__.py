from django.conf import settings

from config.celery import celery_app

__all__ = ["celery_app"]


def toolbar_callback(*_, **__):
    return settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR
