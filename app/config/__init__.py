from django.conf import settings


def toolbar_callback(*_, **__):
    return settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR
