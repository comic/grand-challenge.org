import json

import pytest
from celery.exceptions import MaxRetriesExceededError
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.components.tasks import (
    _retry,
    civ_value_to_file,
    encode_b64j,
    execute_job,
    remove_inactive_container_images,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import MethodFactory
from tests.factories import WorkstationImageFactory


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
    assert new_task.kwargs == {"foo": "bar", "retries": 1}


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
    assert new_task.kwargs == {"foo": "bar", "retries": 1}


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
    assert new_task.kwargs == {"foo": "bar", "retries": 11}


def test_retry_too_many():
    with pytest.raises(MaxRetriesExceededError):
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=100_000,
        )


@pytest.mark.django_db
def test_civ_value_to_file():
    civ = ComponentInterfaceValueFactory(value={"foo": 1, "bar": None})

    civ_value_to_file(civ_pk=civ.pk)

    civ.refresh_from_db()

    with civ.file.open("r") as f:
        v = json.loads(f.read())

    assert v == {"foo": 1, "bar": None}
    assert civ.value is None

    # Check idempotency
    with pytest.raises(RuntimeError):
        civ_value_to_file(civ_pk=civ.pk)


@pytest.mark.parametrize(
    "val,expected",
    (
        (None, "bnVsbA=="),
        (["exec_cmd", "p1_cmd"], "WyJleGVjX2NtZCIsICJwMV9jbWQiXQ=="),
        ("exec_cmd p1_cmd", "ImV4ZWNfY21kIHAxX2NtZCI="),
        ("c\xf7>", "ImNcdTAwZjc+Ig=="),
        ("👍", "Ilx1ZDgzZFx1ZGM0ZCI="),
        ("null", "Im51bGwi"),
    ),
)
def test_encode_b64j(val, expected):
    assert encode_b64j(val=val) == expected


@pytest.mark.django_db
def test_remove_inactive_container_images():
    MethodFactory(is_in_registry=True, is_manifest_valid=True)
    WorkstationImageFactory(is_in_registry=True, is_manifest_valid=True)
    alg = AlgorithmFactory()
    ai1 = AlgorithmImageFactory(
        is_in_registry=True, is_manifest_valid=True, algorithm=alg
    )
    AlgorithmImageFactory(
        is_in_registry=True, is_manifest_valid=True, algorithm=alg
    )

    with capture_on_commit_callbacks() as callbacks:
        remove_inactive_container_images()

    assert len(callbacks) == 1
    # Ensure only the first algorithm image is deleted
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.remove_container_image_from_registry"
        f"(pk={ai1.pk!r}, "
        "app_label='algorithms', model_name='algorithmimage')>"
    )
