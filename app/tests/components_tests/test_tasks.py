import hashlib
import hmac
import io
import json
import uuid
from contextlib import nullcontext
from datetime import timedelta
from pathlib import Path
from unittest.mock import call, patch

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.models import TaskRecord
from requests import put

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    Endpoint,
    EndpointStatusChoices,
    Invocation,
    InvocationStatusChoices,
    Job,
)
from grandchallenge.cases.models import (
    DICOMImageSetUploadStatusChoices,
    RawImageUploadSession,
)
from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
    AmazonSageMakerEndpointOrchestrator,
)
from grandchallenge.components.backends.base import (
    InferenceResult,
    RuntimeSetupResult,
)
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.models import (
    APIMethodChoices,
    ComponentInterfaceValue,
    ComponentJob,
    ImportStatusChoices,
    InterfaceKindChoices,
)
from grandchallenge.components.tasks import (
    _get_image_api_method,
    _get_image_config_and_sha256,
    _repo_login_and_run,
    add_file_to_object,
    add_image_to_object,
    assign_tarball_from_upload,
    delete_container_image,
    encode_b64j,
    handle_endpoint_invocation_event,
    handle_endpoint_status_event,
    invoke_endpoint,
    parse_endpoint_invocation_outputs,
    parse_job_output,
    preload_interactive_algorithms,
    remove_container_image_from_registry,
    remove_inactive_container_images,
    start_endpoint,
    stop_endpoint,
    stop_expired_endpoints,
    update_all_container_image_shims,
    update_container_image_shim,
    upload_to_registry_and_sagemaker,
    validate_container_image,
)
from grandchallenge.core.error_messages import SystemErrorMessages
from grandchallenge.notifications.models import Notification
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmLambdaChoices,
)
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstations.models import WorkstationImage
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
    EndpointFactory,
    InvocationFactory,
)
from tests.archives_tests.factories import ArchiveItemFactory
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    DICOMImageSetUploadFactory,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    EvaluationGroundTruthFactory,
    MethodFactory,
    PhaseFactory,
)
from tests.factories import (
    ImageFactory,
    SessionFactory,
    UserFactory,
    WorkstationImageFactory,
)
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
from tests.utilization_tests.factories import SessionUtilizationFactory


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
        "<bound method SQSLambdaTask._execute of SQSLambdaTask("
        "message=SQSLambdaTaskMessage("
        "task_name='grandchallenge.components.tasks.remove_container_image_from_registry', "
        "kwargs={"
        f"'pk': UUID('{ai1.pk}'), "
        "'app_label': 'algorithms', 'model_name': 'algorithmimage'}, n_retries=0), delay=0, queue='default')>"
    )


@pytest.mark.django_db
def test_validate_container_image(
    invoke_container_image, settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg, image__from_path=invoke_container_image
    )
    assert image.is_manifest_valid is None

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_manifest_valid is True
    assert not image.is_desired_version

    image.is_manifest_valid = None
    image.import_status = ImportStatusChoices.STARTED
    image.save()

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
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
    invoke_container_image, settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg, image__from_path=invoke_container_image
    )
    assert image.is_manifest_valid is None

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image = AlgorithmImage.objects.get(pk=image.pk)
    assert image.is_in_registry
    assert not image.is_desired_version

    image.import_status = ImportStatusChoices.STARTED
    image.save()

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
def test_api_method_extraction(
    invoke_container_image, settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    alg = AlgorithmFactory()
    image = AlgorithmImageFactory(
        algorithm=alg,
        image__from_path=invoke_container_image,
    )
    assert image.api_method == APIMethodChoices.EXEC

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
            pk=image.pk,
            app_label=image._meta.app_label,
            model_name=image._meta.model_name,
            mark_as_desired=False,
        )

    image.refresh_from_db()
    assert image.api_method == APIMethodChoices.INVOKE


def test_api_method_extraction_from_config():
    # If the setting is not found, then default to EXEC
    assert (
        _get_image_api_method(config={"config": {}}) == APIMethodChoices.EXEC
    )
    assert (
        _get_image_api_method(config={"config": {"Labels": {}}})
        == APIMethodChoices.EXEC
    )
    assert (
        _get_image_api_method(
            config={
                "config": {
                    "Labels": {"org.grand-challenge.api-method": "ExEc"}
                }
            }
        )
        == APIMethodChoices.EXEC
    )
    assert (
        _get_image_api_method(
            config={
                "config": {
                    "Labels": {"org.grand-challenge.api-methodddd": "'InVoKe'"}
                }
            }
        )
        == APIMethodChoices.EXEC
    )
    assert (
        _get_image_api_method(
            config={
                "config": {
                    "Labels": {"org.grand-challenge.api-method": "'InVoKe'"}
                }
            }
        )
        == APIMethodChoices.INVOKE
    )
    assert (
        _get_image_api_method(
            config={
                "config": {
                    "Labels": {"Org.grAnd-chAllEngE.ApI-mEthOd": "'InVoKe'"}
                }
            }
        )
        == APIMethodChoices.INVOKE
    )


def test_api_method_extraction_bad_label():
    with pytest.raises(ValidationError) as error:
        _get_image_api_method(
            config={
                "config": {"Labels": {"org.grand-challenge.api-method": "foo"}}
            }
        )

    assert (
        str(error.value)
        == "[\"The label org.grand-challenge.api-method must be one of ['exec', 'invoke'], instead we found 'foo'.\"]"
    )


@pytest.mark.django_db
def test_update_container_image_shim(
    invoke_container_image,
    settings,
    django_capture_on_commit_callbacks,
    tmp_path,
    mocker,
):
    settings.LAMBDA_TASKS_EAGER = True

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
        algorithm=alg, image__from_path=invoke_container_image
    )
    assert image.is_manifest_valid is None

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
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


@pytest.mark.django_db
class TestUpdateContainerImageShimEarlyExits:
    def test_skips_algorithm_image_with_active_job(self):
        ai = AlgorithmImageFactory(latest_shimmed_version="old")
        AlgorithmJobFactory(
            algorithm_image=ai,
            status=Job.EXECUTING,
            time_limit=60,
        )

        result = update_container_image_shim(
            pk=ai.pk,
            app_label=ai._meta.app_label,
            model_name=ai._meta.model_name,
        )

        assert result == "old"

    def test_skips_method_with_active_evaluation(self):
        method = MethodFactory(latest_shimmed_version="old")
        EvaluationFactory(method=method, status=Job.EXECUTING, time_limit=60)

        result = update_container_image_shim(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
        )

        assert result == "old"

    def test_does_not_skip_algorithm_image_without_active_job(self):
        ai = AlgorithmImageFactory(latest_shimmed_version="old")
        AlgorithmJobFactory(
            algorithm_image=ai,
            status=Job.SUCCESS,
            time_limit=60,
        )

        result = update_container_image_shim(
            pk=ai.pk,
            app_label=ai._meta.app_label,
            model_name=ai._meta.model_name,
        )

        # No early exit, but image is not in registry so no shim happens
        assert result == "old"

    def test_does_not_skip_method_without_active_evaluation(self):
        method = MethodFactory(latest_shimmed_version="old")
        EvaluationFactory(method=method, status=Job.SUCCESS, time_limit=60)

        result = update_container_image_shim(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
        )

        # No early exit, but image is not in registry so no shim happens
        assert result == "old"

    def test_raises_not_implemented_for_unknown_model(self):
        wi = WorkstationImageFactory()

        with pytest.raises(NotImplementedError):
            update_container_image_shim(
                pk=wi.pk,
                app_label=wi._meta.app_label,
                model_name=wi._meta.model_name,
            )


@pytest.mark.django_db
class TestUpdateAllContainerImageShims:
    def test_schedules_outdated_executable_images(
        self, settings, django_capture_on_commit_callbacks
    ):
        settings.COMPONENTS_SAGEMAKER_SHIM_VERSION = "new"

        AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            latest_shimmed_version="old",
        )
        MethodFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            latest_shimmed_version="old",
        )

        with django_capture_on_commit_callbacks() as callbacks:
            n_tasks = update_all_container_image_shims()

        assert n_tasks == 2
        assert len(callbacks) == 2
        assert all(
            "grandchallenge.components.tasks.update_container_image_shim"
            in repr(cb)
            for cb in callbacks
        )

    def test_skips_images_already_at_current_version(self, settings):
        settings.COMPONENTS_SAGEMAKER_SHIM_VERSION = "current"

        AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            latest_shimmed_version="current",
        )

        n_tasks = update_all_container_image_shims()

        assert n_tasks == 0

    def test_skips_non_executable_images(self, settings):
        settings.COMPONENTS_SAGEMAKER_SHIM_VERSION = "new"

        AlgorithmImageFactory(
            is_manifest_valid=False,
            is_in_registry=True,
            latest_shimmed_version="old",
        )
        AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=False,
            latest_shimmed_version="old",
        )

        n_tasks = update_all_container_image_shims()

        assert n_tasks == 0


@lambda_task
def some_async_task(*, foo: str):
    return foo


@pytest.mark.parametrize(
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_image_to_object(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = object_factory(**factory_kwargs)
    us = RawImageUploadSessionFactory(status=RawImageUploadSession.SUCCESS)
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)
    ImageFactory(origin=us)

    linked_task = some_async_task.serialize(foo="bar")

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
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_image_to_object_updates_upload_session_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = object_factory(**factory_kwargs)
    us = RawImageUploadSessionFactory(status=RawImageUploadSession.SUCCESS)
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)

    error_message = f"Image validation for socket {ci.title} failed with error: Image imports should result in a single image."

    linked_task = some_async_task.serialize(foo="bar")

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
    settings.LAMBDA_TASKS_EAGER = True

    job = AlgorithmJobFactory(time_limit=10)
    us = RawImageUploadSessionFactory(status=RawImageUploadSession.SUCCESS)
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)

    linked_task = some_async_task.serialize(foo="bar")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=job._meta.app_label,
            model_name=job._meta.model_name,
            upload_session_pk=us.pk,
            object_pk=job.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    job.refresh_from_db()
    assert job.status == job.CANCELLED
    assert job.error_message == "One or more of the inputs failed validation."
    assert "Image imports should result in a single image" in str(
        job.detailed_error_message
    )
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_dicom_image_set_to_object(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = object_factory(**factory_kwargs)
    upload = DICOMImageSetUploadFactory(
        status=DICOMImageSetUploadStatusChoices.COMPLETED
    )
    dicom_image_set = DICOMImageSetFactory(dicom_image_set_upload=upload)
    ImageFactory(dicom_image_set=dicom_image_set)
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.DICOM_IMAGE_SET)

    linked_task = some_async_task.serialize(foo="bar")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            dicom_image_set_upload_pk=upload.pk,
            linked_task=linked_task,
        )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
    assert "some_async_task" in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_dicom_image_set_to_object_updates_upload_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = object_factory(**factory_kwargs)
    # create upload without resulting dicom image set and image.
    upload = DICOMImageSetUploadFactory(
        status=DICOMImageSetUploadStatusChoices.COMPLETED
    )
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.DICOM_IMAGE_SET)

    linked_task = some_async_task.serialize(foo="bar")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            dicom_image_set_upload_pk=upload.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    assert "some_async_task" not in str(callbacks)
    upload.refresh_from_db()
    assert upload.status == DICOMImageSetUploadStatusChoices.FAILED
    assert (
        upload.error_message
        == f"Image validation for socket {ci.title} failed with error: Image imports should result in a single image"
    )


@pytest.mark.django_db
def test_add_dicom_image_set_to_object_marks_job_as_failed_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = AlgorithmJobFactory(time_limit=10)
    # create upload without resulting dicom image set and image.
    upload = DICOMImageSetUploadFactory(
        status=DICOMImageSetUploadStatusChoices.COMPLETED
    )
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.DICOM_IMAGE_SET)

    linked_task = some_async_task.serialize(foo="bar")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            dicom_image_set_upload_pk=upload.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    obj.refresh_from_db()
    assert obj.status == obj.CANCELLED
    assert obj.error_message == "One or more of the inputs failed validation."
    assert "Image imports should result in a single image" in str(
        obj.detailed_error_message
    )
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_dicom_image_set_to_object_sends_notification_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    obj = object_factory(**factory_kwargs)
    # create upload without resulting dicom image set and image.
    upload = DICOMImageSetUploadFactory(
        status=DICOMImageSetUploadStatusChoices.COMPLETED
    )
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.DICOM_IMAGE_SET)
    linked_task = some_async_task.serialize(foo="bar")

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_image_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            interface_pk=ci.pk,
            dicom_image_set_upload_pk=upload.pk,
            linked_task=linked_task,
        )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    assert Notification.objects.count() == 1
    assert (
        f"Image validation for socket {ci.title} failed with error: Image imports should result in a single image"
        in Notification.objects.first().description
    )
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs, context",
    (
        (
            DisplaySetFactory,
            {},
            nullcontext(),
        ),
        (
            ArchiveItemFactory,
            {},
            nullcontext(),
        ),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},  # Required
            pytest.raises(ObjectDoesNotExist),
        ),
    ),
)
@pytest.mark.django_db
def test_task_add_image_to_object_handles_deleted_object(
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
    context,
):
    obj = object_factory(**factory_kwargs)

    linked_task = some_async_task.serialize(foo="bar")
    us = RawImageUploadSessionFactory(status=RawImageUploadSession.SUCCESS)
    ci = ComponentInterfaceFactory(kind="IMG")

    task_kwargs = {
        "app_label": obj._meta.app_label,
        "model_name": obj._meta.model_name,
        "object_pk": obj.pk,
        "linked_task": linked_task,
        "interface_pk": ci.pk,
        "upload_session_pk": us.pk,
    }

    obj.delete()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with context:
            add_image_to_object(**task_kwargs)

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs, context",
    (
        (
            DisplaySetFactory,
            {},
            nullcontext(),
        ),
        (
            ArchiveItemFactory,
            {},
            nullcontext(),
        ),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},  # Required
            pytest.raises(ObjectDoesNotExist),
        ),
    ),
)
@pytest.mark.django_db
def test_task_add_file_to_object_handles_deleted_object(
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
    context,
):
    obj = object_factory(**factory_kwargs)
    user_upload = UserUploadFactory()
    linked_task = some_async_task.serialize(foo="bar")
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)

    task_kwargs = {
        "app_label": obj._meta.app_label,
        "model_name": obj._meta.model_name,
        "object_pk": obj.pk,
        "linked_task": linked_task,
        "interface_pk": ci.pk,
        "user_upload_pk": user_upload.pk,
    }

    obj.delete()

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with context:
            add_file_to_object(**task_kwargs)

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "object_factory, factory_kwargs",
    [
        (DisplaySetFactory, {}),
        (ArchiveItemFactory, {}),
        (
            AlgorithmJobFactory,
            {"time_limit": 10, "status": Job.VALIDATING_INPUTS},
        ),
    ],
)
@pytest.mark.django_db
def test_add_file_to_object(
    settings,
    django_capture_on_commit_callbacks,
    object_factory,
    factory_kwargs,
):
    settings.LAMBDA_TASKS_EAGER = True

    creator = UserFactory()
    obj = object_factory(**factory_kwargs)
    linked_task = some_async_task.serialize(foo="bar")

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'["foo", "bar"]')
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
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

    assert not UserUpload.objects.filter(pk=us.pk).exists()
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
    assert "some_async_task" in str(callbacks)


@pytest.mark.parametrize(
    "object_factory",
    [
        DisplaySetFactory,
        ArchiveItemFactory,
    ],
)
@pytest.mark.django_db
def test_add_file_to_object_sends_notification_on_validation_fail(
    django_capture_on_commit_callbacks,
    object_factory,
):
    creator = UserFactory()
    obj = object_factory()
    linked_task = some_async_task.serialize(foo="bar")

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
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
    assert Notification.objects.count() == 1
    assert (
        f"Validation for socket {ci.title} failed."
        in Notification.objects.first().message
    )
    assert "some_async_task" not in str(callbacks)


@pytest.mark.parametrize(
    "upload_data, expected_error_message",
    [
        (
            b'{"foo": "bar"}',
            "JSON does not fulfill schema: instance is not of type 'array'",
        ),
        (
            b'{"foo": "bar"',
            "The file is not valid JSON. Expecting ',' delimiter:",
        ),
    ],
)
@pytest.mark.django_db
def test_add_file_to_object_updates_job_on_validation_fail(
    settings,
    django_capture_on_commit_callbacks,
    upload_data,
    expected_error_message,
):
    settings.LAMBDA_TASKS_EAGER = True

    creator = UserFactory()
    obj = AlgorithmJobFactory(time_limit=10)
    linked_task = some_async_task.serialize(foo="bar")

    us = UserUploadFactory(filename="file.json", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=upload_data)
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY,
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
    assert "One or more of the inputs failed validation." == obj.error_message
    assert expected_error_message in str(obj.detailed_error_message)
    assert "some_async_task" not in str(callbacks)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind,mock_validator_path",
    (
        (
            InterfaceKindChoices.NEWICK,
            "grandchallenge.components.models.validate_newick_tree_format",
        ),
        (
            InterfaceKindChoices.BIOM,
            "grandchallenge.components.models.validate_biom_format",
        ),
    ),
)
def test_add_file_to_object_validates_kinds(
    kind,
    mock_validator_path,
    settings,
    django_capture_on_commit_callbacks,
    mocker,
):
    settings.LAMBDA_TASKS_EAGER = True

    creator = UserFactory()
    obj = AlgorithmJobFactory(time_limit=10)
    linked_task = some_async_task.serialize(foo="bar")

    us = UserUploadFactory(filename="file.newick", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b"();")
    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()
    ci = ComponentInterfaceFactory(
        kind=kind,
        store_in_database=False,
    )

    mock_validator = mocker.patch(mock_validator_path)

    # Sanity
    mock_validator.assert_not_called()
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        add_file_to_object(
            app_label=obj._meta.app_label,
            model_name=obj._meta.model_name,
            object_pk=obj.pk,
            user_upload_pk=us.pk,
            interface_pk=ci.pk,
            linked_task=linked_task,
        )

    mock_validator.assert_called_once()
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
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
    factory, related_factory, related_model_lookup, field_to_copy
):
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
    assert "with this checksum already exists." in obj2.status
    assert not obj2.user_upload
    with pytest.raises(ValueError):
        getattr(obj2, field_to_copy).file


@pytest.mark.django_db
def test_preload_interactive_algorithms(settings):
    arn = f"arn:aws:lambda:eu-central-1:1234567890:function:org-proj-e-uls23-baseline-{uuid.uuid4()}"

    settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS = {
        "io_bucket_name": "org-proj-e-some-bucket",
        "lambda_functions": [
            {
                # Add a uuid to avoid cache key clashes in testing
                "arn": arn,
                "internal_name": "uls23-baseline",
                "minimum_duration": 1,
                "timeout": 60,
                "version": "1",
            }
        ],
    }

    reader_study = ReaderStudyFactory()
    QuestionFactory(
        reader_study=reader_study,
        interactive_algorithm=InteractiveAlgorithmLambdaChoices.ULS23_BASELINE,
    )

    other_session = SessionFactory(region="other")
    other_session.reader_studies.add(reader_study)

    session = SessionFactory(region="eu-central-1")
    session.reader_studies.add(reader_study)

    session.status = session.STOPPED
    session.save()

    with patch(
        "grandchallenge.components.tasks.InteractiveAlgorithmLambda"
    ) as mock_interactive_algorithm:
        mock_instance = mock_interactive_algorithm.return_value
        mock_instance.consolidate.return_value = "mocked_consolidation_result"

        assert preload_interactive_algorithms() == {
            "uls23-baseline": "mocked_consolidation_result"
        }

        mock_interactive_algorithm.assert_any_call(
            arn=arn,
            qualifier="1",
            should_be_active=True,
        )

        assert mock_instance.consolidate.call_count == 1

    session.status = session.QUEUED
    session.save()

    with patch(
        "grandchallenge.components.tasks.InteractiveAlgorithmLambda"
    ) as mock_interactive_algorithm:
        mock_instance = mock_interactive_algorithm.return_value
        mock_instance.consolidate.return_value = "mocked_consolidation_result"

        assert preload_interactive_algorithms() == {
            "uls23-baseline": "mocked_consolidation_result"
        }

        mock_interactive_algorithm.assert_any_call(
            arn=arn,
            qualifier="1",
            should_be_active=True,
        )

        assert mock_instance.consolidate.call_count == 1


@pytest.mark.django_db
def test_preload_interactive_algorithms_excludes_reader_studies_without_budget(
    settings,
):
    arn = f"arn:aws:lambda:eu-central-1:1234567890:function:org-proj-e-uls23-baseline-{uuid.uuid4()}"

    settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS = {
        "io_bucket_name": "org-proj-e-some-bucket",
        "lambda_functions": [
            {
                # Add a uuid to avoid cache key clashes in testing
                "arn": arn,
                "internal_name": "uls23-baseline",
                "minimum_duration": 1,
                "timeout": 60,
                "version": "1",
            }
        ],
    }

    rs_with_exhausted_credit = ReaderStudyFactory(max_credits=100)
    session_utilization = SessionUtilizationFactory(
        duration=timedelta(hours=1)
    )
    session_utilization.reader_studies.add(rs_with_exhausted_credit)

    QuestionFactory(
        reader_study=rs_with_exhausted_credit,
        interactive_algorithm=InteractiveAlgorithmLambdaChoices.ULS23_BASELINE,
    )

    assert (
        not ReaderStudy.objects.with_has_budget()
        .get(pk=rs_with_exhausted_credit.pk)
        .has_budget
    )

    with patch(
        "grandchallenge.components.tasks.InteractiveAlgorithmLambda"
    ) as mock_interactive_algorithm:
        mock_instance = mock_interactive_algorithm.return_value
        mock_instance.consolidate.return_value = "mocked_consolidation_result"

        assert preload_interactive_algorithms() == {
            "uls23-baseline": "mocked_consolidation_result"
        }

        mock_interactive_algorithm.assert_any_call(
            arn=arn,
            qualifier="1",
            should_be_active=False,
        )

        assert mock_instance.consolidate.call_count == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "image_factory, job_model_factory, image_attribute_name",
    (
        (MethodFactory, EvaluationFactory, "method"),
        (
            AlgorithmImageFactory,
            EvaluationFactory,
            "submission__algorithm_image",
        ),
        (
            AlgorithmImageFactory,
            AlgorithmJobFactory,
            "algorithm_image",
        ),
    ),
)
@pytest.mark.parametrize(
    "job_status, expected_image_is_in_registry",
    (
        (ComponentJob.SUCCESS, False),
        (ComponentJob.FAILURE, False),
        (ComponentJob.PENDING, True),
        (ComponentJob.EXECUTING, True),
    ),
)
def test_remove_container_image_from_registry(
    image_factory,
    job_model_factory,
    image_attribute_name,
    job_status,
    expected_image_is_in_registry,
    mocker,
):
    mocker.patch(
        # remove_tag_from_registry is only implemented for ECR
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    inactive_image = image_factory(
        is_in_registry=True, is_manifest_valid=True, is_desired_version=False
    )

    job_model_factory(
        **{
            image_attribute_name: inactive_image,
            "time_limit": 3600,
            "status": job_status,
        }
    )

    remove_container_image_from_registry(
        pk=inactive_image.pk,
        app_label=inactive_image._meta.app_label,
        model_name=inactive_image._meta.model_name,
    )

    inactive_image.refresh_from_db()
    assert inactive_image.is_in_registry is expected_image_is_in_registry


@pytest.mark.django_db
def test_algorithm_image_protected_from_deletion(mocker):
    algorithm_image = AlgorithmImageFactory()
    job = AlgorithmJobFactory(
        algorithm_image=algorithm_image, status=Job.SUCCESS, time_limit=60
    )
    mock_remove_tag_from_registry = mocker.patch(
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    delete_container_image(
        pk=algorithm_image.pk,
        app_label=algorithm_image._meta.app_label,
        model_name=algorithm_image._meta.model_name,
    )

    algorithm_image.refresh_from_db()
    assert algorithm_image.is_removed is False
    assert mock_remove_tag_from_registry.call_count == 2
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=algorithm_image.shimmed_repo_tag),
            call(repo_tag=algorithm_image.original_repo_tag),
        ]
    )

    job.status = Job.FAILURE
    job.save()

    delete_container_image(
        pk=algorithm_image.pk,
        app_label=algorithm_image._meta.app_label,
        model_name=algorithm_image._meta.model_name,
    )

    algorithm_image.refresh_from_db()
    assert algorithm_image.is_removed is True
    assert mock_remove_tag_from_registry.call_count == 4
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=algorithm_image.shimmed_repo_tag),
            call(repo_tag=algorithm_image.original_repo_tag),
            call(repo_tag=algorithm_image.shimmed_repo_tag),
            call(repo_tag=algorithm_image.original_repo_tag),
        ]
    )


@pytest.mark.django_db
def test_method_protected_from_deletion(mocker):
    method = MethodFactory()
    evaluation = EvaluationFactory(
        method=method, status=Job.SUCCESS, time_limit=60
    )
    mock_remove_tag_from_registry = mocker.patch(
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    delete_container_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method.refresh_from_db()
    assert method.is_removed is False
    assert mock_remove_tag_from_registry.call_count == 2
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=method.shimmed_repo_tag),
            call(repo_tag=method.original_repo_tag),
        ]
    )

    evaluation.status = Job.FAILURE
    evaluation.save()

    delete_container_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method.refresh_from_db()
    assert method.is_removed is True
    assert mock_remove_tag_from_registry.call_count == 4
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=method.shimmed_repo_tag),
            call(repo_tag=method.original_repo_tag),
            call(repo_tag=method.shimmed_repo_tag),
            call(repo_tag=method.original_repo_tag),
        ]
    )


@pytest.mark.django_db
def test_workstation_image_protected_from_deletion(mocker):
    workstation = WorkstationImageFactory()
    mock_remove_tag_from_registry = mocker.patch(
        "grandchallenge.components.tasks.remove_tag_from_registry"
    )

    delete_container_image(
        pk=workstation.pk,
        app_label=workstation._meta.app_label,
        model_name=workstation._meta.model_name,
    )

    workstation.refresh_from_db()
    assert workstation.is_removed is False
    assert mock_remove_tag_from_registry.call_count == 2
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=workstation.shimmed_repo_tag),
            call(repo_tag=workstation.original_repo_tag),
        ]
    )

    WorkstationImage.objects.filter(pk=workstation.pk).update(
        created=now() - relativedelta(months=13)
    )

    delete_container_image(
        pk=workstation.pk,
        app_label=workstation._meta.app_label,
        model_name=workstation._meta.model_name,
    )

    workstation.refresh_from_db()
    assert workstation.is_removed is True
    assert mock_remove_tag_from_registry.call_count == 4
    mock_remove_tag_from_registry.assert_has_calls(
        [
            call(repo_tag=workstation.shimmed_repo_tag),
            call(repo_tag=workstation.original_repo_tag),
            call(repo_tag=workstation.shimmed_repo_tag),
            call(repo_tag=workstation.original_repo_tag),
        ]
    )


start_endpoint_method_names = [
    "provision_auxiliary_data",
    "create_sagemaker_model",
    "create_endpoint_config",
    "create_endpoint",
]


@pytest.mark.django_db
def test_start_endpoint(mocker):
    endpoint = EndpointFactory()
    mock_start_methods = [
        mocker.patch.object(
            AmazonSageMakerEndpointOrchestrator,
            method_name,
        )
        for method_name in start_endpoint_method_names
    ]

    assert endpoint.status != endpoint.StatusChoices.RUNNING

    start_endpoint(**endpoint.task_kwargs)
    endpoint.refresh_from_db()

    for mock_method in mock_start_methods:
        mock_method.assert_called_once()
    assert endpoint.status == endpoint.StatusChoices.STARTED


@pytest.mark.django_db
def test_start_endpoint_wrong_state_raises(mocker):
    endpoint = EndpointFactory(status=EndpointStatusChoices.RUNNING)
    mock_start_methods = [
        mocker.patch.object(
            AmazonSageMakerEndpointOrchestrator,
            method_name,
        )
        for method_name in start_endpoint_method_names
    ]

    assert endpoint.status != endpoint.StatusChoices.QUEUED

    with pytest.raises(RuntimeError, match="not in the expected state"):
        start_endpoint(**endpoint.task_kwargs)

    for mock_method in mock_start_methods:
        mock_method.assert_not_called()
    assert endpoint.status == endpoint.StatusChoices.RUNNING


@pytest.mark.parametrize("method_with_error", start_endpoint_method_names)
@pytest.mark.django_db
def test_start_endpoint_failure(mocker, method_with_error):
    endpoint = EndpointFactory()
    for method_name in start_endpoint_method_names:
        if method_name == method_with_error:
            kwargs = {"side_effect": Exception}
        else:
            kwargs = {}
        mocker.patch.object(
            AmazonSageMakerEndpointOrchestrator,
            method_name,
            **kwargs,
        )
    mock_deprovision_method = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    start_endpoint(**endpoint.task_kwargs)
    endpoint.refresh_from_db()

    assert endpoint.status == endpoint.StatusChoices.FAILED
    assert endpoint.error_message == SystemErrorMessages.UNEXPECTED_ERROR
    mock_deprovision_method.assert_called_once()


@pytest.mark.django_db
def test_start_endpoint_deprovision_failure_raises(mocker):
    endpoint = EndpointFactory()
    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        start_endpoint_method_names[0],
        side_effect=Exception,
    )
    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
        side_effect=Exception("error during deprovision"),
    )
    initial_status = endpoint.status

    # assert failure during deprovision is raised
    with pytest.raises(Exception, match="error during deprovision"):
        start_endpoint(**endpoint.task_kwargs)

    endpoint.refresh_from_db()

    assert endpoint.status == initial_status


@pytest.mark.django_db
def test_stop_endpoint(mocker):
    endpoint = EndpointFactory()
    mock_deprovision_method = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    assert endpoint.status in endpoint.StatusChoices.get_active_choices()

    stop_endpoint(**endpoint.task_kwargs)
    endpoint.refresh_from_db()

    assert endpoint.status == endpoint.StatusChoices.STOPPED
    mock_deprovision_method.assert_called_once()


@pytest.mark.django_db
def test_stop_endpoint_deprovision_failure_raises(mocker):
    endpoint = EndpointFactory()
    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
        side_effect=Exception("error during deprovision"),
    )
    initial_status = endpoint.status

    # assert failure during deprovision is raised
    with pytest.raises(Exception, match="error during deprovision"):
        stop_endpoint(**endpoint.task_kwargs)

    endpoint.refresh_from_db()

    assert endpoint.status == initial_status


@pytest.mark.django_db
def test_stop_endpoint_wrong_state_raises(mocker):
    endpoint = EndpointFactory(status=EndpointStatusChoices.FAILED)
    mock_update_status_method = mocker.patch.object(
        Endpoint,
        "update_status",
    )
    initial_status = endpoint.status

    assert initial_status not in endpoint.StatusChoices.get_active_choices()

    with pytest.raises(Endpoint.DoesNotExist):
        stop_endpoint(**endpoint.task_kwargs)

    endpoint.refresh_from_db()

    assert endpoint.status == initial_status
    mock_update_status_method.assert_not_called()


@pytest.mark.django_db
def test_stop_endpoint_cancels_active_invocations(
    mocker, settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True
    endpoint = EndpointFactory.create(status=EndpointStatusChoices.RUNNING)
    for status in InvocationStatusChoices.get_active_choices():
        InvocationFactory.create(endpoint=endpoint, status=status)
        InvocationFactory.create(status=status)
    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    with django_capture_on_commit_callbacks(execute=True):
        stop_endpoint(**endpoint.task_kwargs)

    for invocation in Invocation.objects.filter(endpoint=endpoint):
        assert invocation.status == InvocationStatusChoices.CANCELLED
    for invocation in Invocation.objects.exclude(endpoint=endpoint):
        assert invocation.status != InvocationStatusChoices.CANCELLED


@pytest.mark.django_db
def test_stop_expired_endpoints(
    settings, mocker, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    EndpointFactory(status=EndpointStatusChoices.RUNNING)
    endpoint_to_stop = EndpointFactory(
        status=EndpointStatusChoices.RUNNING,
        maximum_duration=timedelta(seconds=0),
    )
    EndpointFactory(
        status=EndpointStatusChoices.STOPPED,
        maximum_duration=timedelta(seconds=0),
    )
    mock_deprovision = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    with django_capture_on_commit_callbacks(execute=True):
        stop_expired_endpoints(app_label="algorithms", model_name="endpoint")

    endpoint_to_stop.refresh_from_db()

    mock_deprovision.assert_called_once()
    assert endpoint_to_stop.status == EndpointStatusChoices.STOPPED


@pytest.mark.django_db
def test_handle_endpoint_status_in_service_event(settings):
    endpoint = EndpointFactory(
        status=EndpointStatusChoices.STARTED,
    )
    event = {
        "EndpointName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AE-{endpoint.pk}",
        "EndpointStatus": "IN_SERVICE",
    }

    handle_endpoint_status_event(event=event)
    endpoint.refresh_from_db()

    assert endpoint.status == EndpointStatusChoices.RUNNING


@pytest.mark.django_db
def test_handle_endpoint_status_failed_events(settings, mocker):
    endpoint = EndpointFactory(
        status=EndpointStatusChoices.STARTED,
    )
    event = {
        "EndpointName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AE-{endpoint.pk}",
        "EndpointStatus": "FAILED",
    }
    mock_deprovision = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    handle_endpoint_status_event(event=event)
    endpoint.refresh_from_db()

    mock_deprovision.assert_called_once()
    assert endpoint.status == EndpointStatusChoices.FAILED
    assert endpoint.error_message == SystemErrorMessages.UNEXPECTED_ERROR


@pytest.mark.django_db
def test_handle_endpoint_status_invalid_events(settings, mocker):
    endpoint = EndpointFactory(
        status=EndpointStatusChoices.STARTED,
    )
    event = {
        "EndpointName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AE-{endpoint.pk}",
        "EndpointStatus": "some invalid status",
    }
    mock_deprovision = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    handle_endpoint_status_event(event=event)
    endpoint.refresh_from_db()

    mock_deprovision.assert_called_once()
    assert endpoint.status == EndpointStatusChoices.FAILED
    assert endpoint.error_message == SystemErrorMessages.UNEXPECTED_ERROR


@pytest.mark.parametrize(
    "status",
    set(EndpointStatusChoices).difference([EndpointStatusChoices.STARTED]),
)
@pytest.mark.django_db
def test_handle_endpoint_status_wrong_state_ignored(mocker, settings, status):
    endpoint = EndpointFactory(status=status)
    event = {
        "EndpointName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AE-{endpoint.pk}",
    }
    mock_handle_status_event = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "handle_status_event",
    )

    handle_endpoint_status_event(event=event)
    endpoint.refresh_from_db()

    mock_handle_status_event.assert_not_called()
    assert endpoint.status == status


@pytest.mark.django_db
def test_handle_endpoint_invocation_completed_event(settings):
    invocation = InvocationFactory(
        status=InvocationStatusChoices.EXECUTING,
        endpoint__signing_key=b"itsasecret",
    )
    orchestrator = invocation.orchestrator
    runtime_setup_result = RuntimeSetupResult(
        return_code=0,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    orchestrator._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        Key=orchestrator.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )
    inference_result = InferenceResult(
        pk=f"algorithms-invocation-{invocation.pk}",
        return_code=0,
        user_safe_error_message="",
        user_process_last_stderr_lines=[],
        exec_duration=None,
        invoke_duration=timedelta(seconds=12),
        outputs=[],
        sagemaker_shim_version="0.7.0",
    )
    inference_result_content = inference_result.model_dump_json().encode(
        "utf-8"
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=inference_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    orchestrator._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(inference_result_content),
        Bucket=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        Key=orchestrator._inference_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )
    event = {
        "invocationStatus": "Completed",
        "inferenceId": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AEI-{invocation.pk}",
    }

    handle_endpoint_invocation_event(event=event)
    invocation.refresh_from_db()

    assert invocation.status == invocation.StatusChoices.EXECUTED
    assert invocation.invoke_duration == timedelta(seconds=12)


@pytest.mark.parametrize("status", ("Failed", "Expired"))
@pytest.mark.django_db
def test_handle_endpoint_invocation_failure_events(settings, status):
    invocation = InvocationFactory(
        status=InvocationStatusChoices.EXECUTING,
    )
    event = {
        "invocationStatus": f"{status}",
        "inferenceId": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AEI-{invocation.pk}",
    }

    handle_endpoint_invocation_event(event=event)
    invocation.refresh_from_db()

    assert invocation.status == InvocationStatusChoices.FAILURE
    assert invocation.error_message == SystemErrorMessages.UNEXPECTED_ERROR


@pytest.mark.django_db
def test_handle_endpoint_invocation_invalid_events(settings):
    invocation = InvocationFactory(
        status=InvocationStatusChoices.EXECUTING,
    )
    event = {
        "invocationStatus": "some invalid status",
        "inferenceId": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AEI-{invocation.pk}",
    }

    handle_endpoint_invocation_event(event=event)
    invocation.refresh_from_db()

    assert invocation.status == InvocationStatusChoices.FAILURE
    assert invocation.error_message == SystemErrorMessages.UNEXPECTED_ERROR


@pytest.mark.parametrize(
    "status",
    set(InvocationStatusChoices).difference(
        [InvocationStatusChoices.EXECUTING]
    ),
)
@pytest.mark.django_db
def test_handle_endpoint_invocation_wrong_state_ignored(
    mocker, settings, status
):
    invocation = InvocationFactory(status=status)
    event = {
        "invocationStatus": "Completed",
        "inferenceId": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AEI-{invocation.pk}",
    }
    mock_handle_event = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "handle_event",
    )

    handle_endpoint_invocation_event(event=event)
    invocation.refresh_from_db()

    mock_handle_event.assert_not_called()
    assert invocation.status == status


@pytest.mark.django_db
def test_parse_endpoint_invocation_outputs(settings):
    socket = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    invocation = InvocationFactory(
        status=InvocationStatusChoices.EXECUTED,
        algorithm_interface__outputs=[socket],
    )
    orchestrator = invocation.orchestrator
    content = json.dumps("test output content").encode("utf-8")
    orchestrator._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(content),
        Bucket=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        Key=f"{orchestrator._io_prefix}/{socket.relative_path}",
    )

    assert invocation.outputs.count() == 0

    parse_endpoint_invocation_outputs(**invocation.task_kwargs, event={})
    invocation.refresh_from_db()

    assert invocation.error_message == ""
    assert invocation.status == InvocationStatusChoices.SUCCESS
    assert invocation.outputs.count() == 1

    civ = invocation.outputs.first()

    assert civ.value == "test output content"


@pytest.mark.django_db
def test_parse_endpoint_invocation_outputs_failure(mocker):
    invocation = InvocationFactory(
        status=InvocationStatusChoices.EXECUTED,
    )
    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "create_value_for_output",
        side_effect=Exception,
    )

    parse_endpoint_invocation_outputs(**invocation.task_kwargs, event={})

    invocation.refresh_from_db()

    assert invocation.status == InvocationStatusChoices.FAILURE
    assert invocation.error_message == SystemErrorMessages.UNEXPECTED_ERROR


@pytest.mark.parametrize(
    "status",
    set(InvocationStatusChoices).difference(
        [InvocationStatusChoices.EXECUTED, InvocationStatusChoices.CANCELLED]
    ),
)
@pytest.mark.django_db
def test_parse_endpoint_invocation_outputs_wrong_state_raises(mocker, status):
    invocation = InvocationFactory(status=status)
    mock_create_value_for_output = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "create_value_for_output",
    )

    with pytest.raises(
        RuntimeError, match="Invocation is not ready for output parsing"
    ):
        parse_endpoint_invocation_outputs(**invocation.task_kwargs, event={})
    invocation.refresh_from_db()

    mock_create_value_for_output.assert_not_called()
    assert invocation.status == status
    assert invocation.outputs.count() == 0


@pytest.mark.django_db
def test_parse_endpoint_invocation_outputs_cancelled_skipped(mocker):
    invocation = InvocationFactory(status=InvocationStatusChoices.CANCELLED)
    mock_create_value_for_output = mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "create_value_for_output",
    )

    parse_endpoint_invocation_outputs(**invocation.task_kwargs, event={})
    invocation.refresh_from_db()

    mock_create_value_for_output.assert_not_called()
    assert invocation.status == InvocationStatusChoices.CANCELLED
    assert invocation.outputs.count() == 0


@pytest.mark.django_db
def test_invoke_endpoint_calls_keep_alive(mocker):
    invocation = InvocationFactory.create(
        status=InvocationStatusChoices.PROVISIONED,
    )
    spy_keep_alive = mocker.spy(
        Endpoint,
        "keep_alive",
    )

    invoke_endpoint(**invocation.task_kwargs)

    spy_keep_alive.assert_called_once()


@pytest.mark.django_db
def test_invoke_endpoint_skips_keep_alive_for_reader_study_endpoint(mocker):
    invocation = InvocationFactory.create(
        status=InvocationStatusChoices.PROVISIONED,
    )
    reader_study = ReaderStudyFactory.create()
    invocation.endpoint.endpoint_utilization.reader_studies.add(reader_study)
    spy_keep_alive = mocker.spy(
        Endpoint,
        "keep_alive",
    )

    invoke_endpoint(**invocation.task_kwargs)

    spy_keep_alive.assert_not_called()


class FixedOutputExecutor:
    def create_value_for_output(self, *, interface):
        return ComponentInterfaceValueFactory(interface=interface, value=42)


class RaisedExceptionExecutor:
    def create_value_for_output(self, *, interface):
        raise Exception("Test exception that should not be passed to user")


class RaisedComponentExceptionExecutor:
    def create_value_for_output(self, *, interface):
        raise ComponentException(
            "Test exception that should be passed to user"
        )


@pytest.mark.django_db
def test_parse_job_output(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    int_socket_0, int_socket_1, int_socket_2, int_socket_3 = (
        ComponentInterfaceFactory.create_batch(
            4, kind=InterfaceKindChoices.INTEGER
        )
    )

    interface = AlgorithmInterfaceFactory(
        inputs=[int_socket_0],
        outputs=[int_socket_1, int_socket_2, int_socket_3],
    )
    ai.algorithm.interfaces.add(interface)

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_interface=interface,
        status=Job.PARSING,
        time_limit=60,
    )

    mocker.patch(
        "grandchallenge.algorithms.models.Job.get_executor",
        return_value=FixedOutputExecutor(),
    )

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    job.refresh_from_db()
    assert job.error_message == ""
    assert job.status == Job.SUCCESS
    assert job.outputs.count() == 3


@pytest.mark.django_db
def test_parse_job_output_idempotent(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    int_socket_0, int_socket_1, int_socket_2, int_socket_3 = (
        ComponentInterfaceFactory.create_batch(
            4, kind=InterfaceKindChoices.INTEGER
        )
    )

    interface = AlgorithmInterfaceFactory(
        inputs=[int_socket_0],
        outputs=[int_socket_1, int_socket_2, int_socket_3],
    )
    ai.algorithm.interfaces.add(interface)

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_interface=interface,
        status=Job.PARSING,
        time_limit=60,
    )

    mocker.patch(
        "grandchallenge.algorithms.models.Job.get_executor",
        return_value=FixedOutputExecutor(),
    )

    ComponentInterfaceValue.objects.all().delete()
    assert ComponentInterfaceValue.objects.count() == 0

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    for interface in job.output_interfaces.all():
        assert TaskRecord.objects.filter(
            kwargs__interface_slug=interface.slug
        ).first().result == {"status": f"Value created for {interface.slug}"}

    assert ComponentInterfaceValue.objects.count() == 3

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    for interface in job.output_interfaces.all():
        assert TaskRecord.objects.filter(
            kwargs__interface_slug=interface.slug
        ).first().result == {"status": "Skipping due to job status Succeeded"}

    assert (
        ComponentInterfaceValue.objects.count() == 3
    )  # Still only created 3 outputs

    job.refresh_from_db()
    assert job.error_message == ""
    assert job.status == Job.SUCCESS
    assert job.outputs.count() == 3


@pytest.mark.django_db
def test_parse_job_output_idempotent_still_processing(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    int_socket_0, int_socket_1, int_socket_2 = (
        ComponentInterfaceFactory.create_batch(
            3, kind=InterfaceKindChoices.INTEGER
        )
    )

    interface = AlgorithmInterfaceFactory(
        inputs=[int_socket_0],
        outputs=[int_socket_1, int_socket_2],
    )
    ai.algorithm.interfaces.add(interface)

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_interface=interface,
        status=Job.PARSING,
        time_limit=60,
    )

    mocker.patch(
        "grandchallenge.algorithms.models.Job.get_executor",
        return_value=FixedOutputExecutor(),
    )

    ComponentInterfaceValue.objects.all().delete()
    assert ComponentInterfaceValue.objects.count() == 0

    interface = job.output_interfaces.first()

    with django_capture_on_commit_callbacks(execute=True):
        parse_job_output.execute_on_commit(
            **job.task_kwargs,
            interface_slug=interface.slug,
        )

    assert TaskRecord.objects.filter(
        kwargs__interface_slug=interface.slug
    ).first().result == {"status": f"Value created for {interface.slug}"}

    assert ComponentInterfaceValue.objects.count() == 1

    with django_capture_on_commit_callbacks(execute=True):
        parse_job_output.execute_on_commit(
            **job.task_kwargs,
            interface_slug=interface.slug,
        )

    assert TaskRecord.objects.filter(
        kwargs__interface_slug=interface.slug
    ).first().result == {"status": f"{interface.slug} already exists for job"}

    assert (
        ComponentInterfaceValue.objects.count() == 1
    )  # Still only created 1 outputs

    job.refresh_from_db()
    assert job.error_message == ""
    assert job.status == Job.PARSING
    assert job.outputs.count() == 1


@pytest.mark.django_db
def test_parse_job_output_incorrect_state(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        status=Job.CANCELLED,
        time_limit=60,
    )

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    for interface in job.output_interfaces.all():
        assert TaskRecord.objects.get(
            kwargs__interface_slug=interface.slug
        ).result == {"status": "Skipping due to job status Cancelled"}


@pytest.mark.django_db
def test_parse_job_output_nonexistent_interface(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        status=Job.PARSING,
        time_limit=60,
    )

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    job.refresh_from_db()
    assert job.status == Job.FAILURE
    assert job.error_message in {
        f"Output file '{job.output_interfaces.get().relative_path}' was not produced",
        f"Output directory '{job.output_interfaces.get().relative_path}' is empty",
    }


@pytest.mark.django_db
def test_parse_job_output_executor_exception(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    int_socket_0, int_socket_1, int_socket_2, int_socket_3 = (
        ComponentInterfaceFactory.create_batch(
            4, kind=InterfaceKindChoices.INTEGER
        )
    )

    interface = AlgorithmInterfaceFactory(
        inputs=[int_socket_0],
        outputs=[int_socket_1, int_socket_2, int_socket_3],
    )
    ai.algorithm.interfaces.add(interface)

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_interface=interface,
        status=Job.PARSING,
        time_limit=60,
    )

    mocker.patch(
        "grandchallenge.algorithms.models.Job.get_executor",
        return_value=RaisedExceptionExecutor(),
    )

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    job.refresh_from_db()
    assert job.status == Job.FAILURE
    assert job.error_message == "An unexpected error occurred"


@pytest.mark.django_db
def test_parse_job_output_executor_component_exception(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    ai = AlgorithmImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    int_socket_0, int_socket_1, int_socket_2, int_socket_3 = (
        ComponentInterfaceFactory.create_batch(
            4, kind=InterfaceKindChoices.INTEGER
        )
    )

    interface = AlgorithmInterfaceFactory(
        inputs=[int_socket_0],
        outputs=[int_socket_1, int_socket_2, int_socket_3],
    )
    ai.algorithm.interfaces.add(interface)

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_interface=interface,
        status=Job.PARSING,
        time_limit=60,
    )

    mocker.patch(
        "grandchallenge.algorithms.models.Job.get_executor",
        return_value=RaisedComponentExceptionExecutor(),
    )

    with django_capture_on_commit_callbacks(execute=True):
        for interface in job.output_interfaces.all():
            parse_job_output.execute_on_commit(
                **job.task_kwargs,
                interface_slug=interface.slug,
            )

    job.refresh_from_db()
    assert job.status == Job.FAILURE
    assert job.error_message == "Test exception that should be passed to user"
