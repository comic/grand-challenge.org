from datetime import datetime, timedelta
from pathlib import Path

import pytest
import requests
from actstream.actions import unfollow
from django.conf import settings
from django.core.cache import cache
from django.utils.html import format_html
from redis.exceptions import LockError

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import InterfaceKind
from grandchallenge.components.tasks import (
    push_container_image,
    validate_docker_image,
)
from grandchallenge.evaluation.models import Evaluation, Method, Submission
from grandchallenge.evaluation.tasks import (
    cancel_external_evaluations_past_timeout,
    create_algorithm_jobs_for_evaluation,
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
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory
from tests.uploads_tests.factories import (
    create_completed_upload,
    create_upload_from_file,
)
from tests.utils import get_view_for_user, recurse_callbacks
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_submission_evaluation(
    submission_file,
    settings,
    client,
    django_capture_on_commit_callbacks,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

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
    assert evaluation.stdout.endswith("Greetings from stdout")
    assert evaluation.stderr.endswith('warn("Hello from stderr")')
    assert "UserWarning: Could not google: [Errno " in evaluation.stderr
    assert evaluation.error_message == ""
    assert evaluation.status == evaluation.SUCCESS
    assert (
        evaluation.outputs.get(interface__slug="metrics-json-file").value[
            "acc"
        ]
        == 0.5
    )

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
def test_method_validation(algorithm_io_image):
    """The validator should set the correct sha256 and set the ready bit."""
    method = MethodFactory(image__from_path=algorithm_io_image)

    original_sha256 = method.image_sha256
    assert method.is_manifest_valid is None
    assert method.is_in_registry is False
    assert method.can_execute is False

    validate_docker_image(
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
def test_container_pushing(algorithm_io_image):
    method = MethodFactory(
        image__from_path=algorithm_io_image, is_manifest_valid=True
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


@pytest.mark.django_db
def test_method_validation_invalid_dockerfile(alpine_images):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=alpine_images)
    assert method.is_manifest_valid is None

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
        mark_as_desired=False,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.is_manifest_valid is False
    assert "should only have 1 image" in method.status


@pytest.mark.django_db
def test_method_validation_root_dockerfile(root_image):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=root_image)
    assert method.is_manifest_valid is None

    validate_docker_image(
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

    validate_docker_image(
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


@pytest.mark.django_db
def test_non_zip_submission_failure(
    client,
    submission_file,
    settings,
    django_capture_on_commit_callbacks,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

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
    assert evaluation.error_message.endswith(
        "7z-compressed files are not supported."
    )
    assert evaluation.status == evaluation.FAILURE


@pytest.mark.django_db
def test_evaluation_notifications(
    client,
    algorithm_io_image,
    submission_file,
    settings,
    django_capture_on_commit_callbacks,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Try to upload a submission
    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=10,
    )

    # Add method and upload a submission
    with django_capture_on_commit_callbacks() as callbacks:
        MethodFactory(phase=phase, image__from_path=algorithm_io_image)
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
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
    for recipient in recipients:
        assert str(recipient) in str(Notification.objects.all())
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
    for recipient in recipients:
        assert str(recipient) in str(Notification.objects.all())
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
def test_cancel_external_evaluations_past_timeout(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    challenge = ChallengeFactory()
    participant = UserFactory()
    admin = challenge.admins_group.user_set.get()
    challenge.add_participant(participant)

    e1 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=datetime.now() - timedelta(days=2),
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e2 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=datetime.now() - timedelta(days=2),
        submission__phase__external_evaluation=True,
        submission__phase__challenge=challenge,
        submission__creator=participant,
        time_limit=60,
    )
    e3 = EvaluationFactory(
        status=Evaluation.CLAIMED,
        claimed_at=datetime.now(),
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
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
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
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    input_ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
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
