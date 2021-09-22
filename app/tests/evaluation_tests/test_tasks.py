from pathlib import Path

import pytest
import requests
from actstream.actions import unfollow
from django.conf import settings
from django.test import TestCase
from django.utils.html import format_html
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.tasks import (
    push_container_image,
    validate_docker_image,
)
from grandchallenge.evaluation.models import Evaluation, Method
from grandchallenge.evaluation.tasks import set_evaluation_inputs
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    SubmissionFactory,
)
from tests.utils import recurse_callbacks


@pytest.mark.django_db
def test_submission_evaluation(
    client, evaluation_image, submission_file, settings
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Upload a submission and create an evaluation
    eval_container, sha256 = evaluation_image
    method = MethodFactory(
        image__from_path=eval_container, image_sha256=sha256, ready=True
    )

    # We should not be able to download methods
    with pytest.raises(NotImplementedError):
        _ = method.image.url

    # This will create an evaluation, and we'll wait for it to be executed
    with capture_on_commit_callbacks() as callbacks:
        submission = SubmissionFactory(
            predictions_file__from_path=submission_file, phase=method.phase
        )

    recurse_callbacks(callbacks=callbacks)

    # The evaluation method should return the correct answer
    assert len(submission.evaluation_set.all()) == 1

    evaluation = submission.evaluation_set.first()
    assert evaluation.stdout.endswith("Greetings from stdout\n")
    assert evaluation.stderr.endswith('warn("Hello from stderr")\n')
    assert evaluation.error_message == ""
    assert evaluation.status == evaluation.SUCCESS
    assert (
        evaluation.outputs.get(interface__slug="metrics-json-file").value[
            "acc"
        ]
        == 0.5
    )

    # Try with a csv file
    with capture_on_commit_callbacks() as callbacks:
        submission = SubmissionFactory(
            predictions_file__from_path=Path(__file__).parent
            / "resources"
            / "submission.csv",
            phase=method.phase,
        )

    recurse_callbacks(callbacks=callbacks)

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
def test_method_validation(evaluation_image):
    """The validator should set the correct sha256 and set the ready bit."""
    container, sha256 = evaluation_image
    method = MethodFactory(image__from_path=container)

    # The method factory fakes the sha256 on creation
    assert method.image_sha256 != sha256
    assert method.ready is False

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.image_sha256 == sha256
    assert method.ready is True


@pytest.mark.django_db
def test_container_pushing(evaluation_image):
    container, sha256 = evaluation_image
    method = MethodFactory(image__from_path=container)

    push_container_image(instance=method)

    response = requests.get(
        f"http://{settings.COMPONENTS_REGISTRY_URL}/v2/_catalog"
    )

    assert response.status_code == 200
    assert "gc.localhost/evaluation/method" in response.json()["repositories"]

    response = requests.get(
        f"http://{settings.COMPONENTS_REGISTRY_URL}/v2/gc.localhost/evaluation/method/tags/list"
    )

    assert response.status_code == 200
    assert str(method.pk) in response.json()["tags"]


@pytest.mark.django_db
def test_method_validation_invalid_dockerfile(alpine_images):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=alpine_images)
    assert method.ready is False

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "should only have 1 image" in method.status


@pytest.mark.django_db
def test_method_validation_root_dockerfile(root_image):
    """Uploading two images in a tar archive should fail."""
    method = MethodFactory(image__from_path=root_image)
    assert method.ready is False

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "runs as root" in method.status


@pytest.mark.django_db
def test_method_validation_not_a_docker_tar(submission_file):
    """Upload something that isn't a docker file should be invalid."""
    method = MethodFactory(image__from_path=submission_file)
    assert method.ready is False

    validate_docker_image(
        pk=method.pk,
        app_label=method._meta.app_label,
        model_name=method._meta.model_name,
    )

    method = Method.objects.get(pk=method.pk)
    assert method.ready is False
    assert "manifest.json not found" in method.status


class TestSetEvaluationInputs(TestCase):
    def setUp(self):
        interface = ComponentInterface.objects.get(
            slug="generic-medical-image"
        )

        archive = ArchiveFactory()
        ais = ArchiveItemFactory.create_batch(2)
        archive.items.set(ais)

        input_civs = ComponentInterfaceValueFactory.create_batch(
            2, interface=interface
        )
        output_civs = ComponentInterfaceValueFactory.create_batch(
            2, interface=interface
        )

        for ai, civ in zip(ais, input_civs):
            ai.values.set([civ])

        alg = AlgorithmImageFactory()
        submission = SubmissionFactory(algorithm_image=alg)
        submission.phase.archive = archive
        submission.phase.save()
        submission.phase.algorithm_inputs.set([interface])

        jobs = []
        for inpt, output in zip(input_civs, output_civs):
            j = AlgorithmJobFactory(status=Job.SUCCESS, algorithm_image=alg)
            j.inputs.set([inpt])
            j.outputs.set([output])
            jobs.append(j)

        self.evaluation = EvaluationFactory(
            submission=submission, status=Evaluation.EXECUTING_PREREQUISITES
        )
        self.jobs = jobs
        self.output_civs = output_civs

    def test_unsuccessful_jobs_fail_evaluation(self):
        self.jobs[0].status = Job.FAILURE
        self.jobs[0].save()

        set_evaluation_inputs(evaluation_pk=self.evaluation.pk)

        self.evaluation.refresh_from_db()
        assert self.evaluation.status == self.evaluation.FAILURE
        assert (
            self.evaluation.error_message
            == "The algorithm failed on one or more cases."
        )

    def test_set_evaluation_inputs(self):
        set_evaluation_inputs(evaluation_pk=self.evaluation.pk)

        self.evaluation.refresh_from_db()
        assert self.evaluation.status == self.evaluation.PENDING
        assert self.evaluation.error_message == ""
        assert self.evaluation.inputs.count() == 3
        assert self.evaluation.input_prefixes == {
            str(civ.pk): f"{alg.pk}/output/"
            for alg, civ in zip(self.jobs, self.output_civs)
        }


@pytest.mark.django_db
def test_non_zip_submission_failure(
    client, evaluation_image, submission_file, settings
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Upload a submission and create an evaluation
    eval_container, sha256 = evaluation_image
    method = MethodFactory(
        image__from_path=eval_container, image_sha256=sha256, ready=True
    )

    # Try with a 7z file
    with capture_on_commit_callbacks(execute=True):
        submission = SubmissionFactory(
            predictions_file__from_path=Path(__file__).parent
            / "resources"
            / "submission.7z",
            phase=method.phase,
        )

    # The evaluation method should return the correct answer
    assert len(submission.evaluation_set.all()) == 1
    evaluation = submission.evaluation_set.first()
    assert evaluation.error_message.endswith(
        "7z-compressed files are not supported."
    )
    assert evaluation.status == evaluation.FAILURE


@pytest.mark.django_db
def test_evaluation_notifications(
    client, evaluation_image, submission_file, settings
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Try to upload a submission without a method in place
    with capture_on_commit_callbacks(execute=True):
        submission = SubmissionFactory(
            predictions_file__from_path=submission_file
        )
    # Missing should result in notification for admins of the challenge
    # There are 2 notifications here. The second is about admin addition to the
    # challenge, both notifications are for the admin.
    for notification in Notification.objects.all():
        assert notification.user == submission.phase.challenge.creator
    assert "there is no valid evaluation method" in Notification.objects.filter(
        message="missing method"
    ).get().print_notification(
        user=submission.phase.challenge.creator
    )

    # Add method and upload a submission
    eval_container, sha256 = evaluation_image
    method = MethodFactory(
        image__from_path=eval_container, image_sha256=sha256, ready=True
    )
    # clear notifications for easier testing later
    Notification.objects.all().delete()
    # create submission and wait for it to be evaluated
    with capture_on_commit_callbacks() as callbacks:
        submission = SubmissionFactory(
            predictions_file__from_path=submission_file, phase=method.phase
        )
    recurse_callbacks(callbacks=callbacks)
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
    assert f"There is a new {result_string} for {challenge_string}" in Notification.objects.filter(
        user=recipients[0]
    ).get().print_notification(
        user=recipients[0]
    )
    assert f"Your {submission_string} to {challenge_string} succeeded" in Notification.objects.filter(
        user=recipients[1]
    ).get().print_notification(
        user=recipients[1]
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
    assert f"Your {submission_string} to {challenge_string} failed" in Notification.objects.filter(
        user=recipients[1]
    ).get().print_notification(
        user=recipients[1]
    )

    # check that when admin unsubscribed from phase, they no longer
    # receive notifications about activity related to that phase
    Notification.objects.all().delete()
    unfollow(user=submission.phase.challenge.creator, obj=submission.phase)
    evaluation.update_status(status=evaluation.SUCCESS)
    assert str(submission.phase.challenge.creator) not in str(
        Notification.objects.all()
    )
