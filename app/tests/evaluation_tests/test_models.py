from django.test import TestCase

from grandchallenge.datasets.models import ImageSet
from grandchallenge.evaluation.models import AlgorithmEvaluation
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.evaluation_tests.factories import MethodFactory, SubmissionFactory
from tests.factories import ImageFactory


class TestSubmission(TestCase):
    def setUp(self) -> None:
        self.method = MethodFactory(ready=True)
        self.algorithm_image = AlgorithmImageFactory()

        self.images = ImageFactory.create_batch(3)
        # TODO Fix image set dependency
        imageset = self.method.phase.challenge.imageset_set.get(
            phase=ImageSet.TESTING
        )
        imageset.images.set(self.images[:2])

    def test_algorithm_submission_creates_one_job_per_test_set_image(self):
        SubmissionFactory(
            phase=self.method.phase, algorithm_image=self.algorithm_image,
        )

        assert AlgorithmEvaluation.objects.count() == 2
        assert [
            inpt.image
            for ae in AlgorithmEvaluation.objects.all()
            for inpt in ae.inputs.all()
        ] == self.images[:2]

    def test_create_evaluation_is_idempotent(self):
        s = SubmissionFactory(
            phase=self.method.phase, algorithm_image=self.algorithm_image,
        )
        s.create_evaluation()

        assert AlgorithmEvaluation.objects.count() == 2
