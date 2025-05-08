import pytest

from grandchallenge.core.celery import acks_late_micro_short_task


def test_task_errors_raised_when_invoked(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    counter = 0

    @acks_late_micro_short_task(ignore_errors=(ValueError,))
    def test_task():
        nonlocal counter
        counter += 1
        raise ValueError

    with pytest.raises(ValueError):
        test_task()

    assert counter == 1

    result = test_task.apply_async()

    assert result.status == "SUCCESS"
    assert counter == 2
