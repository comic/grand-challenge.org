import json
from pathlib import Path
from unittest.mock import call

import pytest
from celery.exceptions import MaxRetriesExceededError
from django.core.files.base import ContentFile
from requests import put

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    ImportStatusChoices,
)
from grandchallenge.components.tasks import (
    _get_image_config_and_sha256,
    _repo_login_and_run,
    add_file_to_object,
    add_image_to_object,
    assign_tarball_from_upload,
    civ_value_to_file,
    encode_b64j,
    execute_job,
    remove_inactive_container_images,
    update_container_image_shim,
    upload_to_registry_and_sagemaker,
    validate_docker_image,
)
from grandchallenge.core.celery import _retry, acks_late_micro_short_task
from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveItemFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationGroundTruthFactory,
    MethodFactory,
    PhaseFactory,
)
from tests.factories import ImageFactory, UserFactory, WorkstationImageFactory
from tests.reader_studies_tests.factories import DisplaySetFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)


@pytest.mark.django_db
def test_retry_initial_options(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
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
    assert new_task.kwargs == {"foo": "bar", "_retries": 1}


@pytest.mark.django_db
def test_retry_initial(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=0,
        )
    new_task = callbacks[0].__self__

    assert new_task.options["queue"] == "acks-late-micro-short-delay"
    assert new_task.kwargs == {"foo": "bar", "_retries": 1}


@pytest.mark.django_db
def test_retry_many(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        _retry(
            task=execute_job,
            signature_kwargs={"kwargs": {"foo": "bar"}},
            retries=10,
        )
    new_task = callbacks[0].__self__

    assert new_task.options["queue"] == "acks-late-micro-short-delay"
    assert new_task.kwargs == {"foo": "bar", "_retries": 11}


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
def test_remove_inactive_container_images(django_capture_on_commit_callbacks):
    MethodFactory(
        is_in_registry=True, is_manifest_valid=True, is_desired_version=True
    )
    WorkstationImageFactory(
        is_in_registry=True, is_manifest_valid=True, is_desired_version=True
    )
    alg = AlgorithmFactory()
    ai1 = AlgorithmImageFactory(
        is_in_registry=True, is_manifest_valid=True, algorithm=alg
    )
    AlgorithmImageFactory(
        is_in_registry=True,
        is_manifest_valid=True,
        algorithm=alg,
        is_desired_version=True,
    )

    with django_capture_on_commit_callbacks() as callbacks:
        remove_inactive_container_images()

    assert len(callbacks) == 1
    # Ensure only the first algorithm image is deleted
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.remove_container_image_from_registry"
        f"(pk={ai1.pk!r}, "
        "app_label='algorithms', model_name='algorithmimage')>"
    )


@pytest.mark.django_db
def test_validate_docker_image(
    algorithm_io_image, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg, image__from_path=algorithm_io_image
    )
    assert image.is_manifest_valid is None

    with django_capture_on_commit_callbacks(execute=True):
        validate_docker_image(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_manifest_valid is True
    assert not image.is_desired_version

    image.is_manifest_valid = None
    image.save()

    with django_capture_on_commit_callbacks(execute=True):
        validate_docker_image(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=True,
        )
    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_manifest_valid is True
    assert image.is_desired_version


@pytest.mark.django_db
def test_upload_to_registry_and_sagemaker(
    algorithm_io_image, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        image__from_path=algorithm_io_image,
    )
    assert not image.is_in_registry

    with django_capture_on_commit_callbacks(execute=True):
        upload_to_registry_and_sagemaker(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_in_registry
    assert not image.is_desired_version

    with django_capture_on_commit_callbacks(execute=True):
        upload_to_registry_and_sagemaker(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=True,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_in_registry
    assert image.is_desired_version


@pytest.mark.django_db
def test_update_sagemaker_shim(
    algorithm_io_image,
    settings,
    django_capture_on_commit_callbacks,
    tmp_path,
    mocker,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    mock_remove_tag_from_registry = mocker.patch(
        # remove_tag_from_registry is only implemented for ECR
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    old_version = "alpha"
    new_version = "beta"

    settings.COMPONENTS_SAGEMAKER_SHIM_LOCATION = str(tmp_path)
    settings.COMPONENTS_SAGEMAKER_SHIM_VERSION = old_version

    for version in [old_version, new_version]:
        (tmp_path / f"sagemaker-shim-{version}-Linux-x86_64").touch()

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        image__from_path=algorithm_io_image,
    )
    assert not image.is_in_registry

    with django_capture_on_commit_callbacks(execute=True):
        upload_to_registry_and_sagemaker(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_in_registry
    assert image.latest_shimmed_version == old_version
    assert old_version in image.shimmed_repo_tag

    old_repo_tag = image.shimmed_repo_tag

    output = _repo_login_and_run(
        command=["crane", "manifest", image.shimmed_repo_tag]
    )
    assert output.stdout

    settings.COMPONENTS_SAGEMAKER_SHIM_VERSION = new_version

    with django_capture_on_commit_callbacks(execute=True):
        update_container_image_shim(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_in_registry
    assert image.latest_shimmed_version == new_version
    assert new_version in image.shimmed_repo_tag

    output = _repo_login_and_run(
        command=["crane", "manifest", image.shimmed_repo_tag]
    )
    assert output.stdout

    assert mock_remove_tag_from_registry.call_count == 1

    expected_calls = [
        call(repo_tag=old_repo_tag),
    ]

    mock_remove_tag_from_registry.assert_has_calls(
        expected_calls, any_order=False
    )


@acks_late_micro_short_task
def some_async_task(foo):
    return foo


@pytest.mark.parametrize(
    "object_type, extra_object_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (AlgorithmJobFactory, {"time_limit": 10}),
    ],
)
@pytest.mark.django_db
def test_add_image_to_object(
    settings,
    django_capture_on_commit_callbacks,
    object_type,
    extra_object_kwargs,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    obj = object_type(**extra_object_kwargs)
    us = RawImageUploadSessionFactory()
    ci = ComponentInterfaceFactory(kind="IMG")
    ImageFactory(origin=us)

    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            upload_session_pk=us.pk,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
    assert "some_async_task" in str(callbacks)


@pytest.mark.parametrize(
    "object_type",
    [
        DisplaySetFactory,
        ArchiveItemFactory,
    ],
)
@pytest.mark.django_db
def test_add_image_to_object_updates_upload_session_on_validation_fail(
    settings, django_capture_on_commit_callbacks, object_type
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    obj = object_type()
    us = RawImageUploadSessionFactory()
    ci = ComponentInterfaceFactory(kind="IMG")

    error_message = "Image imports should result in a single image"

    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            upload_session_pk=us.pk,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message
    assert "some_async_task" not in str(callbacks)


@pytest.mark.django_db
def test_add_image_to_object_marks_job_as_failed_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    obj = AlgorithmJobFactory(time_limit=10)
    us = RawImageUploadSessionFactory()
    ci = ComponentInterfaceFactory(kind="IMG")

    error_message = "Image imports should result in a single image"

    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            upload_session_pk=us.pk,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message
    obj.refresh_from_db()
    assert obj.status == obj.CANCELLED
    assert obj.error_message == error_message
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_type, extra_object_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (AlgorithmJobFactory, {"time_limit": 10}),
    ],
)
@pytest.mark.django_db
def test_add_file_to_object(
    settings,
    django_capture_on_commit_callbacks,
    object_type,
    extra_object_kwargs,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()
    obj = object_type(**extra_object_kwargs)
    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'["foo", "bar"]')
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind="JSON",
        store_in_database=False,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_file_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            user_upload_pk=us.pk,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
    assert "some_async_task" in str(callbacks)


@pytest.mark.parametrize(
    "object_type",
    [
        DisplaySetFactory,
        ArchiveItemFactory,
    ],
)
@pytest.mark.django_db
def test_add_file_to_object_sends_notification_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
    object_type,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()
    obj = object_type()
    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind="JSON",
        store_in_database=False,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_file_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            user_upload_pk=us.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert Notification.objects.count() == 1
    assert (
        f"File for interface {ci.title} failed validation"
        in Notification.objects.first().message
    )
    assert "some_async_task" not in str(callbacks)


@pytest.mark.django_db
def test_add_file_to_object_updates_job_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    creator = UserFactory()
    obj = AlgorithmJobFactory(time_limit=10)
    linked_task = some_async_task.signature(
        kwargs={"foo": "bar"}, immutable=True
    )

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind="JSON",
        store_in_database=False,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_file_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            user_upload_pk=us.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    obj.refresh_from_db()
    assert obj.status == obj.CANCELLED
    assert f"File for interface {ci.title} failed validation" in str(
        obj.error_message
    )
    assert Notification.objects.count() == 0
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "container_image_file",
    (
        "hello-scratch-docker-v2.tar.gz",
        "hello-scratch-oci.tar.gz",
    ),
)
@pytest.mark.django_db
def test_get_image_config_and_sha256(container_image_file):
    resource_dir = Path(__file__).parent / "resources"

    ai = AlgorithmImageFactory(image=None)

    with open(resource_dir / container_image_file, "rb") as f:
        ai.image.save(container_image_file, ContentFile(f.read()))

    assert (
        _get_image_config_and_sha256(instance=ai)["image_sha256"]
        == "1bf4ef3c617a6f34a728ec2a5cff1b1dcb926d2d0b93c5bccd830a7918d833da"
    )


@pytest.mark.parametrize(
    "factory,related_factory,related_model_lookup,field_to_copy",
    [
        (
            AlgorithmModelFactory,
            AlgorithmFactory,
            "algorithm",
            "model",
        ),
        (EvaluationGroundTruthFactory, PhaseFactory, "phase", "ground_truth"),
    ],
)
@pytest.mark.django_db()
def test_assign_tarball_from_upload(
    settings, factory, related_factory, related_model_lookup, field_to_copy
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    base_obj = related_factory()
    upload = create_upload_from_file(
        creator=user,
        file_path=Path(__file__).parent
        / "resources"
        / "hello-scratch-oci.tar.gz",
    )
    kwargs = {
        "creator": user,
        "user_upload": upload,
        related_model_lookup: base_obj,
    }
    obj = factory(**kwargs)
    assert obj.is_desired_version is False

    assign_tarball_from_upload(
        app_label=obj._meta.app_label,
        model_name=obj._meta.model_name,
        tarball_pk=obj.pk,
        field_to_copy=field_to_copy,
    )
    obj.refresh_from_db()
    assert obj.is_desired_version
    assert obj.import_status == ImportStatusChoices.COMPLETED

    upload2 = create_upload_from_file(
        creator=user,
        file_path=Path(__file__).parent
        / "resources"
        / "hello-scratch-oci.tar.gz",
    )
    kwargs["user_upload"] = upload2
    obj2 = factory(**kwargs)
    assign_tarball_from_upload(
        app_label=obj2._meta.app_label,
        model_name=obj2._meta.model_name,
        tarball_pk=obj2.pk,
        field_to_copy=field_to_copy,
    )
    obj2.refresh_from_db()
    assert not obj2.is_desired_version
    assert obj2.import_status == ImportStatusChoices.FAILED
    assert "with this sha256 already exists." in obj2.status
    assert not obj2.user_upload
    with pytest.raises(ValueError):
        getattr(obj2, field_to_copy).file
