import pytest
from django.utils.module_loading import import_string

from grandchallenge.core.celery import AcksLateTaskDecorator


def test_all_scheduled_tasks_exist(settings):
    for periodic_task in settings.CELERY_BEAT_SCHEDULE.values():
        try:
            func = import_string(periodic_task["task"])
            assert AcksLateTaskDecorator.is_acks_late_task(func)
        except ImportError:
            pytest.fail(f"Task {periodic_task['task']} does not exist")
