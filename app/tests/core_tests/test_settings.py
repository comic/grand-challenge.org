import pytest
from django.utils.module_loading import import_string


def test_all_scheduled_tasks_exist(settings):
    for periodic_task in settings.CELERY_BEAT_SCHEDULE.values():
        try:
            import_string(periodic_task["task"])
        except ImportError:
            pytest.fail(f"Task {periodic_task['task']} does not exist")
