import pytest
from celery.exceptions import MaxRetriesExceededError
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.components.tasks import _retry, execute_job


@pytest.mark.django_db
def test_retry_initial_options():
    with capture_on_commit_callbacks() as callbacks:
        _retry(
            task=execute_job,
            signature_kwargs={
                "kwargs": {"foo": "bar"},
                "options": {"queue": "mine"},
            },
            retries=0,
        )
    new_task = callbacks[0].__self__

    assert new_task.options["queue"] == "mine-delay"
    assert new_task.kwargs == {
        "foo": "bar",
        "retries": 1,
    }


@pytest.mark.django_db
def test_retry_initial():
    with capture_on_commit_callbacks() as callbacks:
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=0,
        )
    new_task = callbacks[0].__self__

    assert new_task.options["queue"] == "acks-late-micro-short-delay"
    assert new_task.kwargs == {
        "foo": "bar",
        "retries": 1,
    }


@pytest.mark.django_db
def test_retry_many():
    with capture_on_commit_callbacks() as callbacks:
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=10,
        )
    new_task = callbacks[0].__self__

    assert new_task.options["queue"] == "acks-late-micro-short-delay"
    assert new_task.kwargs == {
        "foo": "bar",
        "retries": 11,
    }


def test_retry_too_many():
    with pytest.raises(MaxRetriesExceededError):
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=100_000,
        )
