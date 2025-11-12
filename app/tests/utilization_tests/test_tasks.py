import pytest

from grandchallenge.algorithms.models import Job
from grandchallenge.components.backends.base import Executor
from grandchallenge.utilization.models import JobWarmPoolUtilization
from grandchallenge.utilization.tasks import create_job_warm_pool_utilizations
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory


class UtilizationExecutor(Executor):
    @property
    def external_admin_url(self):
        return ""

    @property
    def warm_pool_retained_billable_time_in_seconds(self):
        return 1337

    @property
    def usd_cents_per_hour(self):
        return 12.1

    @property
    def utilization_duration(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    @staticmethod
    def get_job_name(*, event):
        raise NotImplementedError

    def handle_event(self, *, event):
        raise NotImplementedError

    def runtime_metrics(self):
        raise NotImplementedError

    @staticmethod
    def get_job_params(*, job_name):
        raise NotImplementedError


@pytest.mark.django_db
def test_create_job_warm_pool_utilizations(
    django_assert_num_queries, settings
):
    settings.COMPONENTS_DEFAULT_BACKEND = (
        "tests.utilization_tests.test_tasks.UtilizationExecutor"
    )
    settings.COMPONENTS_USD_TO_EUR = 1

    n_expected_queries = 4

    challenge = ChallengeFactory()
    archive = ArchiveFactory()
    phase = PhaseFactory(challenge=challenge, archive=archive)

    completed_warm_pool_job = AlgorithmJobFactory(
        status=Job.SUCCESS,
        use_warm_pool=True,
        time_limit=60,
    )

    completed_warm_pool_job.job_utilization.challenge = challenge
    completed_warm_pool_job.job_utilization.archive = archive
    completed_warm_pool_job.job_utilization.phase = phase
    completed_warm_pool_job.job_utilization.save()

    # Ignored incomplete job
    AlgorithmJobFactory(
        status=Job.EXECUTING,
        use_warm_pool=True,
        time_limit=60,
    )
    # Ignored non-warm pool job
    AlgorithmJobFactory(
        status=Job.SUCCESS,
        use_warm_pool=False,
        time_limit=60,
    )

    with django_assert_num_queries(n_expected_queries):
        create_job_warm_pool_utilizations()

    warm_pool_utilization = JobWarmPoolUtilization.objects.get()

    assert warm_pool_utilization.creator == completed_warm_pool_job.creator
    assert warm_pool_utilization.phase == phase
    assert warm_pool_utilization.challenge == challenge
    assert warm_pool_utilization.archive == archive
    assert (
        warm_pool_utilization.algorithm_image
        == completed_warm_pool_job.algorithm_image
    )
    assert (
        warm_pool_utilization.algorithm
        == completed_warm_pool_job.algorithm_image.algorithm
    )
    assert warm_pool_utilization.duration.total_seconds() == 1337
    assert warm_pool_utilization.compute_cost_euro_millicents == 4494

    # Run again, check nothing else is created
    with django_assert_num_queries(n_expected_queries - 1):
        create_job_warm_pool_utilizations()

    assert JobWarmPoolUtilization.objects.count() == 1
