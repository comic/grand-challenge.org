from django.test import TestCase, override_settings
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.models import Job
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import MethodFactory, SubmissionFactory
from tests.factories import ImageFactory


class TestSubmission(TestCase):
    def setUp(self) -> None:
        self.method = MethodFactory(
            ready=True, phase__archive=ArchiveFactory()
        )
        self.algorithm_image = AlgorithmImageFactory()

        interface = ComponentInterfaceFactory()
        self.algorithm_image.algorithm.inputs.set([interface])

        self.images = ImageFactory.create_batch(3)

        for image in self.images[:2]:
            civ = ComponentInterfaceValueFactory(
                image=image, interface=interface
            )
            ai = ArchiveItemFactory(archive=self.method.phase.archive)
            ai.values.add(civ)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_algorithm_submission_creates_one_job_per_test_set_image(self):
        with capture_on_commit_callbacks(execute=True):
            SubmissionFactory(
                phase=self.method.phase, algorithm_image=self.algorithm_image,
            )

        assert Job.objects.count() == 2
        assert [
            inpt.image for ae in Job.objects.all() for inpt in ae.inputs.all()
        ] == self.images[:2]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_create_evaluation_is_idempotent(self):
        with capture_on_commit_callbacks(execute=True):
            s = SubmissionFactory(
                phase=self.method.phase, algorithm_image=self.algorithm_image,
            )
            s.create_evaluation()

        assert Job.objects.count() == 2
