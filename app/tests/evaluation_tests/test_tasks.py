import gzip
import io
import json
import os
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest
import requests
from actstream.actions import unfollow
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.html import format_html
from django.utils.timezone import now
from redis.exceptions import LockError

from grandchallenge.algorithms.models import Job
from grandchallenge.challenges.tasks import update_challenge_compute_costs
from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.components.tasks import (
    push_container_image,
    validate_container_image,
)
from grandchallenge.core.error_messages import EvaluationErrorMessages
from grandchallenge.evaluation.models import (
    BatchJob,
    BatchJobTask,
    Evaluation,
    Method,
    Submission,
)
from grandchallenge.evaluation.tasks import (
    cancel_external_evaluations_past_timeout,
    check_prerequisites_for_evaluation_execution,
    create_algorithm_jobs_for_evaluation,
    handle_failed_jobs,
    set_evaluation_inputs,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentTypeChoices
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    BatchJobFactory,
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory
from tests.uploads_tests.factories import (
    create_completed_upload,
    create_upload_from_file,
)
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_submission_evaluation(
    submission_file,
    settings,
    client,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    # Upload a submission and create an evaluation
    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=10,
    )

    method = MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    # We should not be able to download methods
    with pytest.raises(NotImplementedError):
        _ = method.image.url

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    participant = UserFactory()
    VerificationFactory(user=participant, is_verified=True)
    phase.challenge.add_participant(user=participant)

    user_upload = create_upload_from_file(
        creator=participant, file_path=Path(submission_file)
    )
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            client=client,
            method=client.post,
            user=participant,
            viewname="evaluation:submission-create",
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
            },
            data={
                "creator": participant.pk,
                "phase": phase.pk,
                "user_upload": user_upload.pk,
            },
        )

    assert response.status_code == 302
    submission = Submission.objects.get()

    # The evaluation method should return the correct answer
    assert len(submission.evaluation_set.all()) == 1

    evaluation = submission.evaluation_set.first()
    assert evaluation.error_message == ""
    assert evaluation.status == evaluation.SUCCESS
    assert (
        evaluation.outputs.get(interface__slug="metrics-json-file").value[
            "acc"
        ]
        == 0.5
    )
    assert evaluation.exec_duration == timedelta(seconds=1337)
    assert evaluation.invoke_duration == timedelta(seconds=1874)
    assert evaluation.utilization.duration.total_seconds() > 0

    # Try with a csv file
    user_upload = create_upload_from_file(
        creator=participant,
        file_path=Path(__file__).parent / "resources" / "submission.csv",
    )
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            client=client,
            method=client.post,
            user=participant,
            viewname="evaluation:submission-create",
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
            },
            data={
                "creator": participant.pk,
                "phase": phase.pk,
                "user_upload": user_upload.pk,
            },
        )
    assert response.status_code == 302
    submission = Submission.objects.last()
    evaluation = submission.evaluation_set.first()
    assert len(submission.evaluation_set.all()) == 1
    assert evaluation.status == evaluation.SUCCESS
    assert (
        evaluation.outputs.get(interface__slug="metrics-json-file").value[
            "acc"
        ]
        == 0.5
    )


@pytest.mark.django_db
def test_method_validation(
    invoke_container_image, django_capture_on_commit_callbacks, settings
):
    """The validator should set the correct sha256 and set the ready bit."""
    settings.LAMBDA_TASKS_EAGER = True

    method = MethodFactory(image__from_path=invoke_container_image)

    original_sha256 = method.image_sha256
    assert method.is_manifest_valid is None
    assert method.is_in_registry is False
    assert method.can_execute is False

    with django_capture_on_commit_callbacks(execute=True):
        validate_container_image(
            pk=method.pk,
            app_label=method._meta.app_label,
            model_name=method._meta.model_name,
            mark_as_desired=False,
        )

    # The method factory fakes the sha256 on creation
    method = Method.objects.get(pk=method.pk)
    assert method.image_sha256 != original_sha256
    assert method.is_manifest_valid is True
    assert method.is_in_registry is True
    assert method.can_execute is True


@pytest.mark.django_db
def test_container_pushing(invoke_container_image, settings):
    method = MethodFactory(
        image__from_path=invoke_container_image, is_manifest_valid=True
    )

    push_container_image(instance=method)

    response = requests.get(
        f"http://{settings.COMPONENTS_REGISTRY_URL}/v2/_catalog"
    )

    assert response.status_code == 200
    assert "localhost/evaluation/method" in response.json()["repositories"]

    response = requests.get(
        f"http://{settings.COMPONENTS_REGISTRY_URL}/v2/localhost/evaluation/method/tags/list"
    )

    assert response.status_code == 200
    assert str(method.pk) in response.json()["tags"]


@pytest.fixture
def two_invoke_container_image(invoke_container_image):
    # Read all files from the original archive
    with gzip.open(invoke_container_image, "rb") as gz_in:
        with tarfile.open(fileobj=gz_in, mode="r") as tar:
            members = tar.getmembers()
            files = {
                m.name: (m, (f := tar.extractfile(m)) and f.read())
                for m in members
            }

    manifest = json.loads(files["manifest.json"][1])
    original_config_file = manifest[0]["Config"]
    original_config_data = json.loads(files[original_config_file][1])

    # Build two copies with different users
    configs = {}
    for i, user in enumerate(["0", "1000"]):
        config = json.loads(json.dumps(original_config_data))  # deep copy
        config["config"]["User"] = user
        configs[f"image{i}.json"] = json.dumps(config).encode()

    new_manifest = [
        {
            **manifest[0],
            "Config": "image0.json",
            "RepoTags": ["image0:latest"],
        },
        {
            **manifest[0],
            "Config": "image1.json",
            "RepoTags": ["image1:latest"],
        },
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = os.path.join(tmp_dir, "two_images.tar.gz")
        with gzip.open(tmp_path, "wb") as gz_out:
            with tarfile.open(fileobj=gz_out, mode="w") as tar_out:
                # Write all original files except manifest and original config
                for name, (member, data) in files.items():
                    if name in (original_config_file, "manifest.json"):
                        continue
                    if data is not None:
                        member.size = len(data)
                        tar_out.addfile(member, io.BytesIO(data))
                    else:
                        tar_out.addfile(member)

                # Write two config files
                for name, data in configs.items():
                    info = tarfile.TarInfo(name=name)
                    info.size = len(data)
                    tar_out.addfile(info, io.BytesIO(data))

                # Write new manifest
                manifest_data = json.dumps(new_manifest).encode()
                info = tarfile.TarInfo(name="manifest.json")
                info.size = len(manifest_data)
                tar_out.addfile(info, io.BytesIO(manifest_data))

        yield tmp_path


@pytest.mark.django_db
def test_method_validation_two_images(two_invoke_container_image):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=two_invoke_container_image)
    assert method.is_manifest_valid is None

    validate_container_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
        mark_as_desired=False,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.is_manifest_valid is False
    assert "should only have 1 image" in method.status


@pytest.fixture
def invoke_container_image_as_root(invoke_container_image):
    # Read all files from the archive
    with gzip.open(invoke_container_image, "rb") as gz_in:
        with tarfile.open(fileobj=gz_in, mode="r") as tar:
            members = tar.getmembers()
            files = {
                m.name: (m, (f := tar.extractfile(m)) and f.read())
                for m in members
            }

    # Patch the config JSON
    manifest = json.loads(files["manifest.json"][1])
    config_file = manifest[0]["Config"]
    config_data = json.loads(files[config_file][1])
    config_data["config"]["User"] = "0"
    files[config_file] = (
        files[config_file][0],
        json.dumps(config_data).encode(),
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = os.path.join(tmp_dir, "image.tar.gz")
        with gzip.open(tmp_path, "wb") as gz_out:
            with tarfile.open(fileobj=gz_out, mode="w") as tar_out:
                for _, (member, data) in files.items():
                    if data is not None:
                        member.size = len(data)
                        tar_out.addfile(member, io.BytesIO(data))
                    else:
                        tar_out.addfile(member)
        yield tmp_path


@pytest.mark.django_db
def test_method_validation_root_dockerfile(invoke_container_image_as_root):
    """Uploading an image that runs as root should fail."""
    method = MethodFactory(image__from_path=invoke_container_image_as_root)
    assert method.is_manifest_valid is None

    validate_container_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
        mark_as_desired=False,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.is_manifest_valid is False
    assert "runs as root" in method.status


@pytest.mark.django_db
def test_method_validation_not_a_docker_tar(submission_file):
    """Upload something that isn't a docker file should be invalid."""
    method = MethodFactory(image__from_path=submission_file)
    assert method.is_manifest_valid is None

    validate_container_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
        mark_as_desired=False,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.is_manifest_valid is False
    assert method.status == "Could not decompress the container image file."


@pytest.mark.django_db
class TestSetEvaluationInputs:
    def test_set_evaluation_inputs(
        self, submission_without_model_for_optional_inputs
    ):
        eval = EvaluationFactory(
            submission=submission_without_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_without_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )
        set_evaluation_inputs(evaluation_pk=eval.pk)

        eval.refresh_from_db()
        assert eval.status == eval.PENDING
        assert eval.error_message == ""
        assert eval.inputs.count() == 5
        assert eval.input_prefixes == {
            str(civ.pk): f"{alg.pk}/output/"
            for alg, civ in zip(
                submission_without_model_for_optional_inputs.jobs,
                submission_without_model_for_optional_inputs.output_civs,
                strict=True,
            )
        }

    def test_has_pending_jobs(
        self, submission_without_model_for_optional_inputs
    ):
        eval = EvaluationFactory(
            submission=submission_without_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_without_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            status=Job.PENDING,
            creator=None,
            algorithm_image=eval.submission.algorithm_image,
            algorithm_interface=submission_without_model_for_optional_inputs.interface1,
            time_limit=eval.submission.algorithm_image.algorithm.time_limit,
        )
        # nothing happens because there are pending jobs
        set_evaluation_inputs(evaluation_pk=eval.pk)
        eval.refresh_from_db()
        assert eval.status == eval.EXECUTING_PREREQUISITES
        assert eval.inputs.count() == 0
        assert eval.input_prefixes == {}

    def test_has_pending_jobs_with_image_and_model(
        self, submission_with_model_for_optional_inputs
    ):
        evaluation_with_model = EvaluationFactory(
            submission=submission_with_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_with_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            status=Job.PENDING,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_model=evaluation_with_model.submission.algorithm_model,
            algorithm_interface=submission_with_model_for_optional_inputs.interface1,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        # nothing happens
        set_evaluation_inputs(evaluation_pk=evaluation_with_model.pk)
        evaluation_with_model.refresh_from_db()
        assert (
            evaluation_with_model.status
            == evaluation_with_model.EXECUTING_PREREQUISITES
        )
        assert evaluation_with_model.inputs.count() == 0
        assert evaluation_with_model.input_prefixes == {}

    def test_has_pending_jobs_with_image_but_without_model(
        self, submission_with_model_for_optional_inputs
    ):
        evaluation_with_model = EvaluationFactory(
            submission=submission_with_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_with_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )
        # the pending job with only the image will be ignored, but task will still
        # fail because there are no successful jobs with both the image and model yet
        AlgorithmJobFactory(
            status=Job.PENDING,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_interface=submission_with_model_for_optional_inputs.interface1,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        set_evaluation_inputs(evaluation_pk=evaluation_with_model.pk)
        evaluation_with_model.refresh_from_db()
        assert (
            evaluation_with_model.status
            == evaluation_with_model.EXECUTING_PREREQUISITES
        )
        assert evaluation_with_model.inputs.count() == 0
        assert evaluation_with_model.input_prefixes == {}

        # add jobs, 2 for each interface with a model
        j_with_model_1 = AlgorithmJobFactory(
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_model=evaluation_with_model.submission.algorithm_model,
            algorithm_interface=submission_with_model_for_optional_inputs.interface1,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        j_with_model_2 = AlgorithmJobFactory(
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_model=evaluation_with_model.submission.algorithm_model,
            algorithm_interface=submission_with_model_for_optional_inputs.interface1,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        j_with_model_1.inputs.set(
            submission_with_model_for_optional_inputs.jobs[0].inputs.all()
        )
        j_with_model_1.outputs.set(
            submission_with_model_for_optional_inputs.jobs[0].outputs.all()
        )
        j_with_model_2.inputs.set(
            submission_with_model_for_optional_inputs.jobs[1].inputs.all()
        )
        j_with_model_2.outputs.set(
            submission_with_model_for_optional_inputs.jobs[1].outputs.all()
        )

        j_with_model_3 = AlgorithmJobFactory(
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_model=evaluation_with_model.submission.algorithm_model,
            algorithm_interface=submission_with_model_for_optional_inputs.interface2,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        j_with_model_4 = AlgorithmJobFactory(
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=evaluation_with_model.submission.algorithm_image,
            algorithm_model=evaluation_with_model.submission.algorithm_model,
            algorithm_interface=submission_with_model_for_optional_inputs.interface2,
            time_limit=evaluation_with_model.submission.algorithm_image.algorithm.time_limit,
        )
        j_with_model_3.inputs.set(
            submission_with_model_for_optional_inputs.jobs[2].inputs.all()
        )
        j_with_model_3.outputs.set(
            submission_with_model_for_optional_inputs.jobs[2].outputs.all()
        )
        j_with_model_4.inputs.set(
            submission_with_model_for_optional_inputs.jobs[3].inputs.all()
        )
        j_with_model_4.outputs.set(
            submission_with_model_for_optional_inputs.jobs[3].outputs.all()
        )

        jobs = [j_with_model_1, j_with_model_2, j_with_model_3, j_with_model_4]

        set_evaluation_inputs(evaluation_pk=evaluation_with_model.pk)
        evaluation_with_model.refresh_from_db()
        assert evaluation_with_model.status == evaluation_with_model.PENDING
        assert evaluation_with_model.inputs.count() == 5
        assert evaluation_with_model.input_prefixes == {
            str(civ.pk): f"{alg.pk}/output/"
            for alg, civ in zip(
                jobs,
                submission_with_model_for_optional_inputs.output_civs,
                strict=True,
            )
        }

    def test_has_pending_jobs_without_active_model(
        self, submission_without_model_for_optional_inputs
    ):
        eval = EvaluationFactory(
            submission=submission_without_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_without_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            status=Job.PENDING,
            creator=None,
            algorithm_image=eval.submission.algorithm_image,
            algorithm_model=AlgorithmModelFactory(
                algorithm=eval.submission.algorithm_image.algorithm
            ),
            algorithm_interface=submission_without_model_for_optional_inputs.interface1,
            time_limit=eval.submission.algorithm_image.algorithm.time_limit,
        )
        # pending job for image with model should be ignored,
        # since active_model is None for the evaluation
        set_evaluation_inputs(evaluation_pk=eval.pk)
        eval.refresh_from_db()
        assert eval.status == eval.PENDING
        assert eval.inputs.count() == 5
        assert eval.input_prefixes == {
            str(civ.pk): f"{alg.pk}/output/"
            for alg, civ in zip(
                submission_without_model_for_optional_inputs.jobs,
                submission_without_model_for_optional_inputs.output_civs,
                strict=True,
            )
        }

    def test_successful_jobs_without_model(
        self, submission_without_model_for_optional_inputs
    ):
        # delete jobs created in setup(),
        # create new ones with a model, these should not count
        # towards successful jobs, and eval inputs should not be set
        Job.objects.all().delete()

        eval = EvaluationFactory(
            submission=submission_without_model_for_optional_inputs.submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=submission_without_model_for_optional_inputs.submission.phase.evaluation_time_limit,
        )

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            creator=None,
            algorithm_image=submission_without_model_for_optional_inputs.submission.algorithm_image,
            algorithm_interface=submission_without_model_for_optional_inputs.interface1,
            algorithm_model=AlgorithmModelFactory(
                algorithm=eval.submission.algorithm_image.algorithm
            ),
            time_limit=submission_without_model_for_optional_inputs.submission.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [
                submission_without_model_for_optional_inputs.civs_for_interface1[
                    0
                ]
            ]
        )
        j1.outputs.set(
            [submission_without_model_for_optional_inputs.output_civs[0]]
        )
        j2.inputs.set(
            [
                submission_without_model_for_optional_inputs.civs_for_interface1[
                    1
                ]
            ]
        )
        j2.outputs.set(
            [submission_without_model_for_optional_inputs.output_civs[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            creator=None,
            algorithm_image=submission_without_model_for_optional_inputs.submission.algorithm_image,
            algorithm_model=AlgorithmModelFactory(
                algorithm=submission_without_model_for_optional_inputs.submission.algorithm_image.algorithm
            ),
            algorithm_interface=submission_without_model_for_optional_inputs.interface2,
            time_limit=submission_without_model_for_optional_inputs.submission.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            submission_without_model_for_optional_inputs.civs_for_interface2[0]
        )
        j3.outputs.set(
            [submission_without_model_for_optional_inputs.output_civs[2]]
        )
        j4.inputs.set(
            submission_without_model_for_optional_inputs.civs_for_interface2[1]
        )
        j4.outputs.set(
            [submission_without_model_for_optional_inputs.output_civs[3]]
        )

        set_evaluation_inputs(evaluation_pk=eval.pk)
        eval.refresh_from_db()
        assert eval.status == eval.EXECUTING_PREREQUISITES
        assert eval.inputs.count() == 0
        assert eval.input_prefixes == {}

    @staticmethod
    def _build_evaluation(*, archive_item_count):
        # An archive whose items each carry two values, matched by successful
        # jobs that each produce two outputs, so serializing the jobs would
        # N+1 on inputs, outputs, their interfaces/images and the algorithm
        # image unless everything is prefetched.
        ci1, ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=InterfaceKindChoices.BOOL
        )
        output_ci1, output_ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=InterfaceKindChoices.BOOL
        )
        interface = AlgorithmInterfaceFactory(
            inputs=[ci1, ci2], outputs=[output_ci1, output_ci2]
        )
        algorithm_image = AlgorithmImageFactory()
        algorithm_image.algorithm.interfaces.set([interface])

        archive = ArchiveFactory()
        phase = PhaseFactory(
            archive=archive,
            submission_kind=SubmissionKindChoices.ALGORITHM,
        )
        phase.algorithm_interfaces.set([interface])
        submission = SubmissionFactory(
            phase=phase, algorithm_image=algorithm_image
        )
        evaluation = EvaluationFactory(
            submission=submission,
            status=Evaluation.EXECUTING_PREREQUISITES,
            time_limit=phase.evaluation_time_limit,
        )

        for _ in range(archive_item_count):
            input_civs = [
                ComponentInterfaceValueFactory(interface=ci1, value=True),
                ComponentInterfaceValueFactory(interface=ci2, value=False),
            ]
            item = ArchiveItemFactory(archive=archive)
            item.values.set(input_civs)

            job = AlgorithmJobFactory(
                status=Job.SUCCESS,
                creator=None,
                algorithm_image=algorithm_image,
                algorithm_interface=interface,
                time_limit=algorithm_image.algorithm.time_limit,
            )
            job.inputs.set(input_civs)
            job.outputs.set(
                [
                    ComponentInterfaceValueFactory(
                        interface=output_ci1, value=True
                    ),
                    ComponentInterfaceValueFactory(
                        interface=output_ci2, value=False
                    ),
                ]
            )

        return evaluation

    def test_set_evaluation_inputs_query_count_is_constant(self):
        # The number of queries must not grow with the number of archive
        # items / successful jobs / their outputs.
        small_evaluation = self._build_evaluation(archive_item_count=2)
        with CaptureQueriesContext(connection) as captured:
            set_evaluation_inputs(evaluation_pk=small_evaluation.pk)
        baseline_query_count = len(captured.captured_queries)

        small_evaluation.refresh_from_db()
        assert small_evaluation.status == Evaluation.PENDING

        # Five times as many archive items, successful jobs and outputs must
        # not increase the number of queries: everything the serialization
        # reads is prefetched, so there is no per-job query.
        large_evaluation = self._build_evaluation(archive_item_count=10)
        with CaptureQueriesContext(connection) as captured:
            set_evaluation_inputs(evaluation_pk=large_evaluation.pk)

        large_evaluation.refresh_from_db()
        assert large_evaluation.status == Evaluation.PENDING
        assert len(captured.captured_queries) <= baseline_query_count


@pytest.mark.django_db
def test_non_zip_submission_failure(
    client,
    settings,
    submission_file,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=1,
    )

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    participant = UserFactory()
    VerificationFactory(user=participant, is_verified=True)
    phase.challenge.add_participant(user=participant)

    user_upload = create_upload_from_file(
        creator=participant,
        file_path=Path(__file__).parent / "resources" / "submission.7z",
    )
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            client=client,
            method=client.post,
            user=participant,
            viewname="evaluation:submission-create",
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
            },
            data={
                "creator": participant.pk,
                "phase": phase.pk,
                "user_upload": user_upload.pk,
            },
        )

    assert response.status_code == 302

    submission = Submission.objects.get()
    # The evaluation method should return the correct answer
    assert len(submission.evaluation_set.all()) == 1
    evaluation = submission.evaluation_set.first()
    assert (
        evaluation.error_message == EvaluationErrorMessages.UNSUPPORTED_INPUT
    )
    assert evaluation.status == evaluation.FAILURE


@pytest.mark.django_db
def test_evaluation_notifications(
    client,
    settings,
    submission_file,
    django_capture_on_commit_callbacks,
):
    settings.LAMBDA_TASKS_EAGER = True

    # Try to upload a submission
    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=10,
    )

    # Add method and upload a submission
    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    participant = UserFactory()
    VerificationFactory(user=participant, is_verified=True)
    phase.challenge.add_participant(user=participant)

    user_upload = create_upload_from_file(
        creator=participant, file_path=Path(submission_file)
    )
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    Notification.objects.all().delete()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            client=client,
            method=client.post,
            user=participant,
            viewname="evaluation:submission-create",
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
            },
            data={
                "creator": participant.pk,
                "phase": phase.pk,
                "user_upload": user_upload.pk,
            },
        )

    assert response.status_code == 302
    submission = Submission.objects.get()

    # creator of submission and admins of challenge should get notification
    # about successful submission
    recipients = list(submission.phase.challenge.get_admins())
    recipients.append(submission.creator)
    assert Notification.objects.count() == len(recipients)
    assert {*recipients} == {n.user for n in Notification.objects.all()}
    result_string = format_html(
        '<a href="{}">result</a>', submission.get_absolute_url()
    )
    submission_string = format_html(
        '<a href="{}">submission</a>', submission.get_absolute_url()
    )
    challenge_string = format_html(
        '<a href="{}">{}</a>',
        submission.phase.challenge.get_absolute_url(),
        submission.phase.challenge.short_name,
    )
    assert (
        f"There is a new {result_string} for {challenge_string}"
        in Notification.objects.filter(user=recipients[0])
        .get()
        .print_notification(user=recipients[0])
    )
    assert (
        f"Your {submission_string} to {challenge_string} succeeded"
        in Notification.objects.filter(user=recipients[1])
        .get()
        .print_notification(user=recipients[1])
    )

    Notification.objects.all().delete()

    # update evaluation status to failed
    evaluation = submission.evaluation_set.first()
    evaluation.update_status(status=evaluation.FAILURE)
    assert evaluation.status == evaluation.FAILURE
    # notifications for admin and creator of submission
    assert Notification.objects.count() == len(recipients)
    assert {*recipients} == {n.user for n in Notification.objects.all()}
    assert f"The {submission_string} from {user_profile_link(Notification.objects.filter(user=recipients[0]).get().actor)} to {challenge_string} failed" in Notification.objects.filter(
        user=recipients[0]
    ).get().print_notification(
        user=recipients[0]
    )
    assert (
        f"Your {submission_string} to {challenge_string} failed"
        in Notification.objects.filter(user=recipients[1])
        .get()
        .print_notification(user=recipients[1])
    )

    # check that when admin unsubscribed from phase, they no longer
    # receive notifications about activity related to that phase
    Notification.objects.all().delete()
    unfollow(user=submission.phase.challenge.creator, obj=submission.phase)
    evaluation.update_status(status=evaluation.SUCCESS)
    assert str(submission.phase.challenge.creator) not in str(
        Notification.objects.all()
    )


def test_cache_lock():
    # Used in create_algorithm_jobs_for_evaluation
    with cache.lock("foo", timeout=5, blocking_timeout=1):
        try:
            with cache.lock("foo", timeout=5, blocking_timeout=1):
                raise RuntimeError("Test failed, shouldn't hit this line")
        except LockError:
            assert True


@pytest.mark.django_db
def test_cancel_external_evaluations_past_timeout():
    challenge = ChallengeFactory()
    participant = UserFactory()
    admin = challenge.admins_group.user_set.get()
    challenge.add_participant(participant)

    e1 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=now() - timedelta(days=2),
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e2 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=now() - timedelta(days=2),
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e3 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=now(),
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e4 = EvaluationFactory(
        status=Evaluation.SUCCESS,
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e5 = EvaluationFactory(
        status=Evaluation.FAILURE,
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e6 = EvaluationFactory(
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )

    # reset notifications
    Notification.objects.all().delete()

    cancel_external_evaluations_past_timeout()

    e1.refresh_from_db()
    e2.refresh_from_db()
    e3.refresh_from_db()
    e4.refresh_from_db()
    e5.refresh_from_db()
    e6.refresh_from_db()

    assert e1.status == Evaluation.CANCELLED
    assert e2.status == Evaluation.CANCELLED
    assert e1.error_message == "External evaluation timed out."
    assert e2.error_message == "External evaluation timed out."
    for e in [e3, e4, e5, e6]:
        assert e.status != Evaluation.CANCELLED
        assert e.error_message == ""

    assert Notification.objects.count() == 4
    receivers = [
        notification.user for notification in Notification.objects.all()
    ]
    assert {admin, participant} == set(receivers)
    for notification in Notification.objects.all():
        assert (
            "External evaluation timed out."
            in notification.print_notification(user=notification.user)
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "evaluation_time_limit",
    (300, 43200),
)
def test_evaluation_time_limit_set(
    django_capture_on_commit_callbacks, client, evaluation_time_limit
):
    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=1,
        evaluation_time_limit=evaluation_time_limit,
    )

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    participant = UserFactory()
    VerificationFactory(user=participant, is_verified=True)
    phase.challenge.add_participant(user=participant)

    user_upload = create_completed_upload(user=participant)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=participant,
        viewname="evaluation:submission-create",
        reverse_kwargs={
            "challenge_short_name": phase.challenge.short_name,
            "slug": phase.slug,
        },
        data={
            "creator": participant.pk,
            "phase": phase.pk,
            "user_upload": user_upload.pk,
        },
    )

    assert response.status_code == 302

    submission = Submission.objects.get()
    evaluation = submission.evaluation_set.get()
    assert evaluation.time_limit == evaluation_time_limit


@pytest.mark.django_db
def test_evaluation_order_with_title():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__algorithm_image=ai,
        time_limit=ai.algorithm.time_limit,
        status=Evaluation.PENDING,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    # Priority should be given to archive items with titles
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.add(ComponentInterfaceValueFactory(interface=input_ci))

    civs = ComponentInterfaceValueFactory.create_batch(5, interface=input_ci)

    for idx, civ in enumerate(civs):
        archive_item = ArchiveItemFactory(archive=archive, title=f"{5 - idx}")
        archive_item.values.add(civ)

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=True
    )

    job = Job.objects.get()

    expected_civ = civs[-1]

    assert expected_civ.archive_items.first().title == "1"
    assert {*job.inputs.all()} == {expected_civ}


@pytest.mark.django_db
def test_evaluation_order_without_title():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__algorithm_image=ai,
        time_limit=ai.algorithm.time_limit,
        status=Evaluation.PENDING,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])

    evaluation.submission.phase.algorithm_interfaces.set([interface])

    civs = ComponentInterfaceValueFactory.create_batch(5, interface=input_ci)

    for civ in civs:
        archive_item = ArchiveItemFactory(archive=archive)
        archive_item.values.add(civ)

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=True
    )

    job = Job.objects.get()

    expected_civ = civs[0]

    assert {*job.inputs.all()} == {expected_civ}


@pytest.mark.django_db
def test_create_algorithm_jobs_for_evaluation_batch_mode(settings):
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__phase__algorithm_time_limit=600,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.PENDING,
    )
    settings.EVALUATION_MAXIMUM_BATCH_JOB_DURATION = (
        1500  # 2 tasks per batch + set-up time
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    # Five archive items -> ceil(5 / 2) = 3 batch jobs (2, 2, 1)
    civs = ComponentInterfaceValueFactory.create_batch(5, interface=input_ci)
    for civ in civs:
        archive_item = ArchiveItemFactory(archive=archive)
        archive_item.values.add(civ)

    # first_run schedules a single batch job (matching the per-item throttle)
    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=True
    )

    assert BatchJob.objects.count() == 1
    first_batch_job = BatchJob.objects.get()
    assert first_batch_job.tasks.count() == 2
    assert not Job.objects.exists()

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.EXECUTING_PREREQUISITES

    # Subsequent runs schedule the remaining batch jobs
    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=False
    )

    batch_jobs = list(BatchJob.objects.all())
    assert len(batch_jobs) == 3

    task_counts = sorted(bj.tasks.count() for bj in batch_jobs)
    assert task_counts == [1, 2, 2]

    # Every task is created against the phase interface with the archive
    # item's inputs, and the whole-job time limit is the sum of the per-task
    # limits.
    for batch_job in batch_jobs:
        assert batch_job.submission == evaluation.submission
        assert batch_job.algorithm_image == ai
        assert batch_job.time_limit == 600
        for task in batch_job.tasks.all():
            assert task.algorithm_interface == interface
            assert task.inputs.count() == 1

    # All archive item inputs are covered exactly once across all tasks
    scheduled_inputs = {
        civ
        for batch_job in batch_jobs
        for task in batch_job.tasks.all()
        for civ in task.inputs.all()
    }
    assert scheduled_inputs == {*civs}


@pytest.mark.django_db
def test_create_algorithm_jobs_for_evaluation_batch_mode_no_items():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__algorithm_image=ai,
        time_limit=ai.algorithm.time_limit,
        status=Evaluation.PENDING,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=True
    )

    assert not BatchJob.objects.exists()
    assert not BatchJobTask.objects.exists()

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.EXECUTING_PREREQUISITES


@pytest.mark.django_db
def test_create_algorithm_jobs_for_evaluation_invoice_workflow():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    submission = SubmissionFactory(phase__archive=archive, algorithm_image=ai)
    challenge = submission.phase.challenge
    invoice = InvoiceFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission=submission,
        time_limit=ai.algorithm.time_limit,
        status=Evaluation.PENDING,
    )
    evaluation.utilization.invoice = invoice
    evaluation.utilization.save()
    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])

    evaluation.submission.phase.algorithm_interfaces.set([interface])

    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.add(ComponentInterfaceValueFactory(interface=input_ci))

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=True
    )

    assert Job.objects.count() == 1, "Sanity: creates jobs"
    job = Job.objects.get()
    assert job.utilization.invoice == invoice
    assert job.status == Job.PENDING


@pytest.mark.django_db
def test_set_evaluation_inputs_for_batch_submission():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__algorithm_image=ai,
        time_limit=60,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    output_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(
        inputs=[input_ci], outputs=[output_ci]
    )
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    input_civs = []
    for _ in range(2):
        civ = ComponentInterfaceValueFactory(interface=input_ci)
        archive_item = ArchiveItemFactory(archive=archive)
        archive_item.values.add(civ)
        input_civs.append(civ)

    batch_job = BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{civ} for civ in input_civs],
        status=BatchJob.SUCCESS,
        time_limit=ai.algorithm.time_limit,
    )

    output_civ_for_task = {}
    for task in batch_job.tasks.all():
        output_civ = ComponentInterfaceValueFactory(interface=output_ci)
        task.outputs.add(output_civ)
        output_civ_for_task[task] = output_civ

    set_evaluation_inputs(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.PENDING
    assert evaluation.error_message == ""

    predictions_civ = evaluation.inputs.get(
        interface__slug="predictions-json-file"
    )
    # predictions.json is a list of BatchJobTasks (one per archive item)
    assert len(predictions_civ.value) == 2
    assert {entry["pk"] for entry in predictions_civ.value} == {
        str(task.pk) for task in output_civ_for_task
    }

    assert evaluation.input_prefixes == {
        str(output_civ.pk): f"{task.pk}/output/"
        for task, output_civ in output_civ_for_task.items()
    }
    for output_civ in output_civ_for_task.values():
        assert output_civ in evaluation.inputs.all()


@pytest.mark.django_db
def test_set_evaluation_inputs_excludes_stale_batch_tasks():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    output_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(
        inputs=[input_ci], outputs=[output_ci]
    )
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    # A single archive item exists now
    current_civ = ComponentInterfaceValueFactory(interface=input_ci)
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.add(current_civ)

    # A previously-run batch task processed a value set that no longer
    # corresponds to any archive item (the item was since edited)
    stale_civ = ComponentInterfaceValueFactory(interface=input_ci)
    stale_batch_job = BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{stale_civ}],
        status=BatchJob.SUCCESS,
        time_limit=ai.algorithm.time_limit,
    )
    stale_task = stale_batch_job.tasks.get()
    stale_task.outputs.add(ComponentInterfaceValueFactory(interface=output_ci))

    # The submission is not complete: the stale task does not count, and the
    # current archive item has no successful task yet.
    assert not evaluation.inputs_complete

    # Run the task for the current archive item
    current_batch_job = BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{current_civ}],
        status=BatchJob.SUCCESS,
        time_limit=ai.algorithm.time_limit,
    )
    current_task = current_batch_job.tasks.get()
    current_output_civ = ComponentInterfaceValueFactory(interface=output_ci)
    current_task.outputs.add(current_output_civ)

    del evaluation.successful_inference_tasks_per_interface
    del evaluation.successful_inference_task_count_per_interface
    del evaluation.total_successful_inference_tasks
    del evaluation.inputs_complete
    assert evaluation.inputs_complete

    set_evaluation_inputs(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.PENDING

    predictions_civ = evaluation.inputs.get(
        interface__slug="predictions-json-file"
    )
    # Only the current task is present; the stale task is excluded
    assert [entry["pk"] for entry in predictions_civ.value] == [
        str(current_task.pk)
    ]
    assert evaluation.input_prefixes == {
        str(current_output_civ.pk): f"{current_task.pk}/output/"
    }


@pytest.mark.django_db
def test_set_evaluation_inputs_for_batch_submission_with_pending_jobs():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    civ = ComponentInterfaceValueFactory(interface=input_ci)
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.add(civ)

    BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{civ}],
        status=BatchJob.PENDING,
        time_limit=ai.algorithm.time_limit,
    )

    set_evaluation_inputs(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.EXECUTING_PREREQUISITES
    assert evaluation.inputs.count() == 0
    assert evaluation.input_prefixes == {}


@pytest.mark.django_db
def test_handle_failed_jobs_cancels_batch_jobs():
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    pending_batch_job = BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{ComponentInterfaceValueFactory(interface=input_ci)}],
        status=BatchJob.PENDING,
        time_limit=ai.algorithm.time_limit,
    )
    successful_batch_job = BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{ComponentInterfaceValueFactory(interface=input_ci)}],
        status=BatchJob.SUCCESS,
        time_limit=ai.algorithm.time_limit,
    )

    handle_failed_jobs(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.FAILURE

    pending_batch_job.refresh_from_db()
    assert pending_batch_job.status == BatchJob.CANCELLED

    successful_batch_job.refresh_from_db()
    assert successful_batch_job.status == BatchJob.SUCCESS


@pytest.mark.django_db
def test_check_prerequisites_blocked_by_failed_batch_job(mocker):
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__phase__submission_kind=SubmissionKindChoices.ALGORITHM,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.VALIDATING_INPUTS,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    # A single valid archive item, processed by a batch job that failed.
    civ = ComponentInterfaceValueFactory(interface=input_ci)
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.set([civ])

    BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{civ}],
        status=BatchJob.FAILURE,
        time_limit=ai.algorithm.time_limit,
    )

    mocked_execute = mocker.patch(
        "grandchallenge.evaluation.tasks.prepare_and_execute_evaluation"
    )

    check_prerequisites_for_evaluation_execution(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.CANCELLED
    assert EvaluationErrorMessages.UNSUCCESSFUL_JOBS in str(
        evaluation.error_message
    )
    mocked_execute.execute_on_commit.assert_not_called()


@pytest.mark.django_db
def test_check_prerequisites_proceeds_when_batch_jobs_successful(mocker):
    ai = AlgorithmImageFactory()
    archive = ArchiveFactory()
    evaluation = EvaluationFactory(
        submission__phase__archive=archive,
        submission__phase__use_batch_mode=True,
        submission__phase__submission_kind=SubmissionKindChoices.ALGORITHM,
        submission__algorithm_image=ai,
        time_limit=10,
        status=Evaluation.VALIDATING_INPUTS,
    )

    input_ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    interface = AlgorithmInterfaceFactory(inputs=[input_ci])
    ai.algorithm.interfaces.set([interface])
    evaluation.submission.phase.algorithm_interfaces.set([interface])

    civ = ComponentInterfaceValueFactory(interface=input_ci)
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.set([civ])

    BatchJobFactory(
        submission=evaluation.submission,
        algorithm_image=ai,
        algorithm_interface=interface,
        input_civ_sets=[{civ}],
        status=BatchJob.SUCCESS,
        time_limit=ai.algorithm.time_limit,
    )

    mocked_execute = mocker.patch(
        "grandchallenge.evaluation.tasks.prepare_and_execute_evaluation"
    )

    check_prerequisites_for_evaluation_execution(evaluation_pk=evaluation.pk)

    evaluation.refresh_from_db()
    assert evaluation.status == Evaluation.VALIDATING_INPUTS
    mocked_execute.execute_on_commit.assert_called_once_with(
        evaluation_pk=evaluation.pk
    )


@pytest.mark.django_db
def test_average_algorithm_job_duration_includes_batch_jobs(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    phase = PhaseFactory(challenge=challenge)

    job = AlgorithmJobFactory(status=Job.SUCCESS, time_limit=60)
    job_utilization = job.job_utilization
    job_utilization.phase = phase
    job_utilization.challenge = challenge
    job_utilization.duration = timedelta(minutes=5)
    job_utilization.save()

    batch_job = BatchJobFactory(
        submission__phase=phase,
        status=BatchJob.SUCCESS,
        time_limit=60,
    )
    batch_job_utilization = batch_job.utilization
    batch_job_utilization.phase = phase
    batch_job_utilization.challenge = challenge
    batch_job_utilization.duration = timedelta(minutes=15)
    batch_job_utilization.save()

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    phase.refresh_from_db()
    # Average of the two per-type averages: (5 + 15) / 2
    assert phase.average_algorithm_job_duration == timedelta(minutes=10)


@pytest.mark.django_db
def test_average_algorithm_job_duration_none_without_jobs(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    phase = PhaseFactory(challenge=challenge)

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    phase.refresh_from_db()
    assert phase.average_algorithm_job_duration is None
