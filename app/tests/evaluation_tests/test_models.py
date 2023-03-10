from datetime import timedelta
from itertools import chain

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import now
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.models import Job
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.tasks import create_evaluation
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ImageFactory, UserFactory


class TestSubmission(TestCase):
    def setUp(self) -> None:
        self.method = MethodFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            phase__archive=ArchiveFactory(),
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
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    def test_algorithm_submission_creates_one_job_per_test_set_image(self):
        s = SubmissionFactory(
            phase=self.method.phase, algorithm_image=self.algorithm_image
        )

        with capture_on_commit_callbacks() as callbacks:
            create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

        # Execute the callbacks non-recursively
        for c in callbacks:
            c()

        assert Job.objects.count() == 2
        assert [
            inpt.image for ae in Job.objects.all() for inpt in ae.inputs.all()
        ] == self.images[:2]

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @override_settings(CELERY_TASK_EAGER_PROPAGATES=True)
    def test_create_evaluation_is_idempotent(self):
        s = SubmissionFactory(
            phase=self.method.phase, algorithm_image=self.algorithm_image
        )

        with capture_on_commit_callbacks(execute=False) as callbacks1:
            create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

        with capture_on_commit_callbacks(execute=False) as callbacks2:
            create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

        # Execute the callbacks non-recursively
        for c in chain(callbacks1, callbacks2):
            c()

        assert Job.objects.count() == 2


@pytest.mark.django_db
class TestPhaseLimits:
    def setup_method(self):
        self.phase = PhaseFactory()
        self.user = UserFactory()
        evaluation_kwargs = {
            "submission__creator": self.user,
            "submission__phase": self.phase,
            "status": Evaluation.SUCCESS,
        }
        now = timezone.now()

        # Failed evaluations don't count
        e = EvaluationFactory(
            submission__creator=self.user,
            submission__phase=self.phase,
            status=Evaluation.FAILURE,
        )
        # Other users evaluations don't count
        EvaluationFactory(
            submission__creator=UserFactory(),
            submission__phase=self.phase,
            status=Evaluation.SUCCESS,
        )
        # Other phases don't count
        EvaluationFactory(
            submission__creator=self.user,
            submission__phase=PhaseFactory(),
            status=Evaluation.SUCCESS,
        )

        # Evaluations 1, 2 and 7 days ago
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=1) + timedelta(hours=1)
        e.submission.save()
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=2) + timedelta(hours=1)
        e.submission.save()
        e = EvaluationFactory(**evaluation_kwargs)
        e.submission.created = now - timedelta(days=7) + timedelta(hours=1)
        e.submission.save()

    @pytest.mark.parametrize("submission_limit_period", (None, 1, 3))
    def test_submissions_closed(self, submission_limit_period):
        self.phase.submissions_limit_per_user_per_period = 0
        self.phase.submission_limit_period = submission_limit_period

        i = self.phase.get_next_submission(user=UserFactory())

        assert i["remaining_submissions"] == 0
        assert i["next_submission_at"] is None

    @pytest.mark.parametrize(
        "submission_limit_period,expected_remaining", ((1, 2), (3, 1), (28, 0))
    )
    def test_submissions_period(
        self, submission_limit_period, expected_remaining
    ):
        self.phase.submissions_limit_per_user_per_period = (
            3  # successful jobs created in setUp
        )
        self.phase.submission_limit_period = submission_limit_period

        i = self.phase.get_next_submission(user=self.user)

        assert i["remaining_submissions"] == expected_remaining
        assert i["next_submission_at"] is not None

    @pytest.mark.parametrize(
        "submissions_limit_per_user_per_period,expected_remaining",
        ((4, 1), (3, 0), (1, 0)),
    )
    def test_submissions_period_none(
        self, submissions_limit_per_user_per_period, expected_remaining
    ):
        self.phase.submissions_limit_per_user_per_period = (
            submissions_limit_per_user_per_period
        )
        self.phase.submission_limit_period = None

        i = self.phase.get_next_submission(user=self.user)

        assert i["remaining_submissions"] == expected_remaining
        if expected_remaining > 0:
            assert i["next_submission_at"] is not None
        else:
            assert i["next_submission_at"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "submissions_limit_per_user_per_period,submissions_open,submissions_close,submissions_limit,open_for_submissions,expected_status",
    [
        (0, None, None, 10, False, "Not accepting submissions"),
        (
            0,
            now() - timedelta(days=1),
            None,
            10,
            False,
            "Not accepting submissions",
        ),
        (
            0,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            10,
            False,
            "completed",
        ),
        (
            0,
            now() - timedelta(days=10),
            now() + timedelta(days=1),
            10,
            False,
            "Not accepting submissions",
        ),
        (
            0,
            now() + timedelta(days=10),
            None,
            10,
            False,
            "Opening submissions",
        ),
        (
            0,
            now() + timedelta(days=10),
            now() + timedelta(days=15),
            10,
            False,
            "Opening submissions",
        ),
        (0, None, now() - timedelta(days=15), 10, False, "completed"),
        (
            0,
            None,
            now() + timedelta(days=15),
            10,
            False,
            "Not accepting submissions",
        ),
        (10, None, None, 10, True, "Accepting submissions"),
        (
            10,
            now() - timedelta(days=1),
            None,
            10,
            True,
            "Accepting submissions",
        ),
        (
            10,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            10,
            False,
            "completed",
        ),
        (
            10,
            now() - timedelta(days=10),
            now() + timedelta(days=1),
            10,
            True,
            "Accepting submissions",
        ),
        (
            10,
            now() + timedelta(days=10),
            None,
            10,
            False,
            "Opening submissions",
        ),
        (
            10,
            now() + timedelta(days=10),
            now() + timedelta(days=15),
            10,
            False,
            "Opening submissions",
        ),
        (10, None, None, 1, False, "Not accepting submissions"),
        (10, None, None, None, True, "Accepting submissions"),
    ],
)
def test_open_for_submission(
    submissions_limit_per_user_per_period,
    submissions_open,
    submissions_close,
    submissions_limit,
    open_for_submissions,
    expected_status,
):
    phase = PhaseFactory()
    phase.submissions_limit_per_user_per_period = (
        submissions_limit_per_user_per_period
    )
    phase.submissions_open_at = submissions_open
    phase.submissions_close_at = submissions_close
    phase.total_number_of_submissions_allowed = submissions_limit
    phase.save()

    SubmissionFactory.create_batch(5, phase=phase)

    assert phase.open_for_submissions == open_for_submissions
    assert expected_status in phase.submission_status_string
