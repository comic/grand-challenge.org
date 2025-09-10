from collections import namedtuple
from contextlib import nullcontext
from datetime import timedelta
from typing import NamedTuple

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import now

from grandchallenge.algorithms.forms import RESERVED_SOCKET_SLUGS
from grandchallenge.algorithms.models import Job
from grandchallenge.archives.models import ArchiveItem
from grandchallenge.components.models import (
    CIVData,
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.models import (
    SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT,
    CombinedLeaderboard,
    Evaluation,
    Method,
    Phase,
    PhaseAdditionalEvaluationInput,
    get_archive_items_for_interfaces,
    get_valid_jobs_for_interfaces_and_archive_items,
)
from grandchallenge.evaluation.tasks import (
    calculate_ranks,
    create_algorithm_jobs_for_evaluation,
    update_combined_leaderboard,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentTypeChoices
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
    CombinedLeaderboardFactory,
    EvaluationFactory,
    EvaluationGroundTruthFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory, ImageFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.fixture
def algorithm_submission():
    algorithm_submission = namedtuple(
        "algorithm_submission", ["method", "algorithm_image", "images"]
    )

    method = MethodFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        phase__archive=ArchiveFactory(),
    )
    algorithm_image = AlgorithmImageFactory()

    ci = ComponentInterfaceFactory()
    interface = AlgorithmInterfaceFactory(inputs=[ci])
    algorithm_image.algorithm.interfaces.set([interface])

    images = ImageFactory.create_batch(3)

    for image in images[:2]:
        civ = ComponentInterfaceValueFactory(image=image, interface=ci)
        ai = ArchiveItemFactory(archive=method.phase.archive)
        ai.values.add(civ)

    return algorithm_submission(
        method=method, algorithm_image=algorithm_image, images=images
    )


@pytest.mark.django_db
def test_algorithm_submission_creates_one_job_per_test_set_image(
    django_capture_on_commit_callbacks, settings, algorithm_submission
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s = SubmissionFactory(
        phase=algorithm_submission.method.phase,
        algorithm_image=algorithm_submission.algorithm_image,
    )
    eval = EvaluationFactory(
        submission=s,
        method=algorithm_submission.method,
        time_limit=60,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    with django_capture_on_commit_callbacks(execute=True):
        create_algorithm_jobs_for_evaluation(
            evaluation_pk=eval.pk, first_run=False
        )

    assert Job.objects.count() == 2
    assert [
        inpt.image for ae in Job.objects.all() for inpt in ae.inputs.all()
    ] == algorithm_submission.images[:2]


@pytest.mark.django_db
def test_create_evaluation_is_idempotent(
    django_capture_on_commit_callbacks, settings, algorithm_submission
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s = SubmissionFactory(
        phase=algorithm_submission.method.phase,
        algorithm_image=algorithm_submission.algorithm_image,
    )

    with django_capture_on_commit_callbacks(execute=True):
        s.create_evaluation(additional_inputs=None)

    with django_capture_on_commit_callbacks(execute=True):
        s.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 1
    # max_inital_jobs is set to 1, so only one job should be created
    assert Job.objects.count() == 1


@pytest.mark.django_db
def test_create_evaluation_sets_gpu_and_memory():
    method = MethodFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        phase__evaluation_requires_gpu_type=GPUTypeChoices.V100,
        phase__evaluation_requires_memory_gb=1337,
    )

    submission = SubmissionFactory(phase=method.phase)

    submission.create_evaluation(additional_inputs=None)

    evaluation = Evaluation.objects.get()

    assert evaluation.requires_gpu_type == GPUTypeChoices.V100
    assert evaluation.requires_memory_gb == 1337


@pytest.mark.django_db
def test_create_algorithm_jobs_for_evaluation_sets_gpu_and_memory():
    inputs = [ComponentInterfaceFactory()]
    outputs = [ComponentInterfaceFactory()]

    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    interface = AlgorithmInterfaceFactory(inputs=inputs, outputs=outputs)
    algorithm_image.algorithm.interfaces.set([interface])

    archive = ArchiveFactory()
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.set(
        [
            ComponentInterfaceValueFactory(interface=interface)
            for interface in inputs
        ]
    )

    phase = PhaseFactory(
        archive=archive,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        submissions_limit_per_user_per_period=1,
    )
    phase.algorithm_interfaces.set([interface])

    method = MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    evaluation = EvaluationFactory(
        method=method,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.K80,
        requires_memory_gb=123,
        submission__phase=phase,
        submission__algorithm_image=algorithm_image,
        submission__algorithm_requires_gpu_type=GPUTypeChoices.V100,
        submission__algorithm_requires_memory_gb=456,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=False
    )

    job = Job.objects.get()

    assert job.requires_gpu_type == GPUTypeChoices.V100
    assert job.requires_memory_gb == 456


@pytest.mark.django_db
def test_create_evaluation_uniqueness_checks(
    django_capture_on_commit_callbacks, settings, algorithm_submission
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    sub = SubmissionFactory(
        phase=algorithm_submission.method.phase,
        algorithm_image=algorithm_submission.algorithm_image,
    )

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 1

    gt = EvaluationGroundTruthFactory(phase=sub.phase, is_desired_version=True)
    del sub.phase.active_ground_truth
    assert sub.phase.active_ground_truth == gt

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 2

    m = MethodFactory(
        phase=sub.phase, is_in_registry=True, is_manifest_valid=True
    )
    m.mark_desired_version()
    del sub.phase.active_image
    assert sub.phase.active_image == m

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 3

    sub.phase.evaluation_time_limit = 45
    sub.phase.save()

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 4

    sub.phase.evaluation_requires_gpu_type = GPUTypeChoices.A10G
    sub.phase.save()

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 5

    sub.phase.evaluation_requires_memory_gb = 16
    sub.phase.save()

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 6

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(additional_inputs=None)

    assert Evaluation.objects.count() == 6

    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    sub.phase.additional_evaluation_inputs.set([ci])
    ComponentInterfaceValueFactory(interface=ci, value="foo")
    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(
            additional_inputs=[CIVData(interface_slug=ci.slug, value="foo")]
        )

    assert Evaluation.objects.count() == 7

    with django_capture_on_commit_callbacks(execute=True):
        sub.create_evaluation(
            additional_inputs=[CIVData(interface_slug=ci.slug, value="foo")]
        )

    assert Evaluation.objects.count() == 7


@pytest.mark.django_db
class TestPhaseLimits:
    def setup_method(self):
        phase = PhaseFactory()

        InvoiceFactory(
            challenge=phase.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        self.phase = Phase.objects.get(pk=phase.pk)
        self.user = UserFactory()

        evaluation_kwargs = {
            "submission__creator": self.user,
            "submission__phase": self.phase,
            "status": Evaluation.SUCCESS,
            "time_limit": self.phase.evaluation_time_limit,
        }
        now = timezone.now()

        # Failed evaluations don't count
        EvaluationFactory(
            submission__creator=self.user,
            submission__phase=self.phase,
            status=Evaluation.FAILURE,
            time_limit=self.phase.evaluation_time_limit,
        )
        # Other users evaluations don't count
        EvaluationFactory(
            submission__creator=UserFactory(),
            submission__phase=self.phase,
            status=Evaluation.SUCCESS,
            time_limit=self.phase.evaluation_time_limit,
        )
        # Other phases don't count
        EvaluationFactory(
            submission__creator=self.user,
            submission__phase=PhaseFactory(),
            status=Evaluation.SUCCESS,
            time_limit=self.phase.evaluation_time_limit,
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
    "submissions_limit_per_user_per_period,submissions_open,submissions_close,compute_costs_euros,open_for_submissions,expected_status",
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
        (10, None, None, 10, True, "Accepting submissions"),
    ],
)
def test_open_for_submission(
    submissions_limit_per_user_per_period,
    submissions_open,
    submissions_close,
    compute_costs_euros,
    open_for_submissions,
    expected_status,
):
    PhaseFactory()

    # Annotate the compute costs
    phase = Phase.objects.get()

    phase.submissions_limit_per_user_per_period = (
        submissions_limit_per_user_per_period
    )
    phase.submissions_open_at = submissions_open
    phase.submissions_close_at = submissions_close
    phase.save()

    phase.challenge.compute_cost_euro_millicents = 5 * 1000 * 100
    phase.challenge.save()

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=compute_costs_euros,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    # Fetch from the db to get the cost annotations
    # Maybe this is solved with GeneratedField (Django 5)?
    phase = Phase.objects.get(pk=phase.pk)

    assert phase.open_for_submissions == open_for_submissions
    assert expected_status in phase.submission_status_string


@pytest.mark.django_db
def test_combined_leaderboards(
    django_capture_on_commit_callbacks, django_assert_max_num_queries
):
    challenge = ChallengeFactory()
    phases = PhaseFactory.create_batch(
        2,
        challenge=challenge,
        score_jsonpath="result",
        score_default_sort="asc",
    )
    users = UserFactory.create_batch(3)
    leaderboard = CombinedLeaderboardFactory(challenge=challenge)
    leaderboard.phases.set(challenge.phase_set.all())
    interface = ComponentInterface.objects.get(slug="metrics-json-file")

    results = {  # Lower is better
        0: {
            0: (1, 2),
            1: (1, 2),
        },
        1: {
            0: (3, 3),
            1: (2, 3),
        },
        2: {
            0: (2, 3),
            1: (2, 3),
        },
    }

    for phase_idx, phase in enumerate(phases):
        for user_idx, user in enumerate(users):
            for result in results[user_idx][phase_idx]:
                evaluation = EvaluationFactory(
                    submission__creator=user,
                    submission__phase=phase,
                    published=True,
                    status=Evaluation.SUCCESS,
                    time_limit=phase.evaluation_time_limit,
                )

                output_civ, _ = evaluation.outputs.get_or_create(
                    interface=interface
                )
                output_civ.value = {"result": result}
                output_civ.save()

        with django_capture_on_commit_callbacks() as callbacks:
            calculate_ranks(phase_pk=phase.pk)

        assert len(callbacks) == 1
        assert (
            repr(callbacks[0])
            == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
        )

    with django_assert_max_num_queries(7):
        update_combined_leaderboard(pk=leaderboard.pk)

    assert (
        Evaluation.objects.filter(
            submission__phase__challenge=challenge
        ).count()
        == 12
    )
    assert (
        Evaluation.objects.filter(
            submission__phase__challenge=challenge, rank=1
        ).count()
        == 2
    )

    ranks = leaderboard.combined_ranks

    assert ranks[0]["combined_rank"] == 1
    assert ranks[0]["user"] == users[0].username
    assert ranks[1]["combined_rank"] == 2
    assert ranks[1]["user"] == users[2].username
    assert ranks[2]["combined_rank"] == 3
    assert ranks[2]["user"] == users[1].username


@pytest.mark.django_db
def test_combined_leaderboards_with_non_public_components():
    challenge = ChallengeFactory()
    phases = PhaseFactory.create_batch(
        2,
        challenge=challenge,
        score_jsonpath="result",
        score_default_sort="asc",
    )
    users = UserFactory.create_batch(3)
    leaderboard = CombinedLeaderboardFactory(
        challenge=challenge,
        combination_method=CombinedLeaderboard.CombinationMethodChoices.SUM,
    )
    leaderboard.phases.set(challenge.phase_set.all())
    interface = ComponentInterface.objects.get(slug="metrics-json-file")

    results = (
        {  # Lower is better, values reflect the rank generated evaluation have
            0: {
                0: (1, 2, 7),
                1: (1, 2),
            },
            1: {
                0: (3, 4),
                1: (3, 4),
            },
            2: {
                0: (5, 6),
                1: (5, 6),
            },
        }
    )

    for phase_idx, phase in enumerate(phases):
        for user_idx, user in enumerate(users):
            for result in results[user_idx][phase_idx]:
                evaluation = EvaluationFactory(
                    submission__creator=user,
                    submission__phase=phase,
                    published=True,
                    status=Evaluation.SUCCESS,
                    time_limit=phase.evaluation_time_limit,
                )

                output_civ, _ = evaluation.outputs.get_or_create(
                    interface=interface
                )
                output_civ.value = {"result": result}
                output_civ.save()

    def update_leaderboards():
        # The following are normally scheduled async but for testing purposes
        # we call them directly
        for p in phases:
            calculate_ranks(phase_pk=p.pk)
        update_combined_leaderboard(pk=leaderboard.pk)

        # clear cached property
        if hasattr(leaderboard, "_combined_ranks_object"):
            del leaderboard._combined_ranks_object

    update_leaderboards()

    assert (  # Sanity check
        Evaluation.objects.filter(
            submission__phase__challenge=challenge
        ).count()
        == 13
    )
    assert (  # Sanity check
        Evaluation.objects.filter(
            submission__phase__challenge=challenge, rank=1
        ).count()
        == 2
    )

    ranks = leaderboard.combined_ranks

    # Default ranks, user 0 is ranked first
    assert ranks[0]["combined_rank"] == 2
    assert ranks[0]["user"] == users[0].username
    assert ranks[1]["combined_rank"] == 6
    assert ranks[1]["user"] == users[1].username
    assert ranks[2]["combined_rank"] == 10
    assert ranks[2]["user"] == users[2].username

    # Retract the two best evaluations of user 0
    phase = phases[0]
    for rank in [1, 2]:
        evaluation = Evaluation.objects.get(
            submission__creator=users[0],
            submission__phase=phase,
            rank=rank,
        )
        evaluation.published = False
        evaluation.save()

    update_leaderboards()
    new_ranks = leaderboard.combined_ranks

    # New eval scores: 3, 4, 5, 6, 7
    # New eval rank:   1, 2, 3, 4, 5

    # New ranking should result in:
    # user 0: 1 + 5 = 6
    # user 1: 3 + 1 = 4
    # user 2: 5 + 3 = 8

    assert new_ranks[0]["combined_rank"] == 4
    assert new_ranks[0]["user"] == users[1].username
    assert new_ranks[1]["combined_rank"] == 6
    assert new_ranks[1]["user"] == users[0].username
    assert new_ranks[2]["combined_rank"] == 8
    assert new_ranks[2]["user"] == users[2].username

    # Retracting a phase should result in an empty leaderboard
    phase.public = False
    phase.save()

    update_leaderboards()
    assert len(leaderboard.combined_ranks) == 0


@pytest.mark.django_db
def test_combined_leaderboard_updated_on_save(
    django_capture_on_commit_callbacks,
):
    leaderboard = CombinedLeaderboardFactory()

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.save()

    assert len(callbacks) == 1
    assert (
        repr(callbacks[0])
        == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
    )


@pytest.mark.django_db
def test_combined_leaderboard_updated_on_phase_change(
    django_capture_on_commit_callbacks,
):
    leaderboard = CombinedLeaderboardFactory()
    phase = PhaseFactory()

    def assert_callbacks(callbacks):
        assert len(callbacks) == 1
        assert (
            repr(callbacks[0])
            == f"<bound method Signature.apply_async of grandchallenge.evaluation.tasks.update_combined_leaderboard(pk={leaderboard.pk!r})>"
        )

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.add(phase)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.remove(phase)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.set([phase])

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        leaderboard.phases.clear()

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.add(leaderboard)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.remove(leaderboard)

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.set([leaderboard])

    assert_callbacks(callbacks)

    with django_capture_on_commit_callbacks() as callbacks:
        phase.combinedleaderboard_set.clear()

    assert_callbacks(callbacks)


@pytest.mark.parametrize(
    "combined_ranks,expected_ranks",
    (
        ([], []),
        ([10, 20, 30], [1, 2, 3]),
        ([10, 20, 20, 30], [1, 2, 2, 4]),
    ),
)
def test_combined_leaderboard_ranks(combined_ranks, expected_ranks):
    combined_ranks = [{"combined_rank": cr} for cr in combined_ranks]
    CombinedLeaderboard._rank_combined_rank_scores(combined_ranks)
    assert [cr["rank"] for cr in combined_ranks] == expected_ranks


@pytest.mark.parametrize(
    "eval_metrics_json_file_value, expected_invalid_metrics",
    (
        (
            {
                "acc": {"std": 0.1, "mean": 0.0},
                "dice": {"std": 0.2, "mean": 0.5},
            },
            set(),
        ),
        (
            {
                "acc": {"std": 0.1, "mean": 0.0},
                "dice": {"std": 0.2, "mean": 0.5},
            },
            set(),
        ),
        (
            {"acc": {"std": 0.1, "mean": 0.0}},
            {"dice.mean"},
        ),
        (
            {"dice": {"std": 0.2, "mean": 0.5}},
            {"acc.mean"},
        ),
        (
            {"cosine": {"std": 0.1, "mean": 0.0}},
            {"acc.mean", "dice.mean"},
        ),
        (
            {
                "acc": {"std": 0.1, "mean": 0.0},
                "dice": {"std": 0.2, "mean": {"oops": "an object"}},
            },
            {"dice.mean"},
        ),
    ),
)
@pytest.mark.django_db
def test_evaluation_invalid_metrics(
    eval_metrics_json_file_value,
    expected_invalid_metrics,
):
    phase = PhaseFactory(
        challenge__hidden=False,
        public=True,
        score_jsonpath="acc.mean",
        score_title="Accuracy Mean",
        extra_results_columns=[
            {"path": "dice.mean", "order": "asc", "title": "Dice mean"}
        ],
    )

    evaluation = EvaluationFactory(
        submission__phase=phase, time_limit=phase.evaluation_time_limit
    )

    ci = ComponentInterface.objects.get(slug="metrics-json-file")
    civ = ComponentInterfaceValueFactory(
        interface=ci, value=eval_metrics_json_file_value
    )

    evaluation.outputs.set([civ])

    assert evaluation.invalid_metrics == expected_invalid_metrics


@pytest.mark.django_db
def test_valid_archive_items_per_interface():
    archive = ArchiveFactory()
    phase = PhaseFactory(archive=archive)
    i1, i2, i3 = ComponentInterfaceFactory.create_batch(3)
    interface = AlgorithmInterfaceFactory(inputs=[i1, i2])
    phase.algorithm_interfaces.set([interface])

    # Valid archive item
    ai1 = ArchiveItemFactory(archive=archive)
    ai1.values.add(ComponentInterfaceValueFactory(interface=i1))
    ai1.values.add(ComponentInterfaceValueFactory(interface=i2))

    # Invalid, because it has extra value
    ai2 = ArchiveItemFactory(archive=archive)
    ai2.values.add(ComponentInterfaceValueFactory(interface=i1))
    ai2.values.add(ComponentInterfaceValueFactory(interface=i2))
    ai2.values.add(ComponentInterfaceValueFactory(interface=i3))

    # Invalid, missing all values
    _ = ArchiveItemFactory(archive=archive)

    # Invalid, incomplete
    ai4 = ArchiveItemFactory(archive=archive)
    ai4.values.add(ComponentInterfaceValueFactory(interface=i1))

    # Invalid, incomplete but right number of values
    ai5 = ArchiveItemFactory(archive=archive)
    ai5.values.add(ComponentInterfaceValueFactory(interface=i1))
    ai5.values.add(ComponentInterfaceValueFactory(interface=i3))

    civ1 = ComponentInterfaceValueFactory(interface=i1)
    civ2 = ComponentInterfaceValueFactory(interface=i2)

    # Valid, reusing interfaces
    ai6 = ArchiveItemFactory(archive=archive)
    ai6.values.set([civ1, civ2])
    ai7 = ArchiveItemFactory(archive=archive)
    ai7.values.set([civ1, civ2])

    assert phase.valid_archive_items_per_interface.keys() == {interface}
    assert [
        item.pk
        for qs in phase.valid_archive_items_per_interface.values()
        for item in qs.order_by("pk")
    ] == [
        item.pk
        for item in ArchiveItem.objects.filter(
            pk__in=[ai1.pk, ai6.pk, ai7.pk]
        ).order_by("pk")
    ]


@pytest.mark.django_db
def test_email_sent_to_editors_when_permissions_enabled():
    editors = UserFactory.create_batch(2)

    challenge = ChallengeFactory()

    for editor in editors:
        VerificationFactory(user=editor, is_verified=True)
        challenge.add_admin(user=editor)

    mail.outbox.clear()

    phase = PhaseFactory(challenge=challenge)

    phase.give_algorithm_editors_job_view_permissions = True
    phase.save()

    assert len(mail.outbox) == len(challenge.admins_group.user_set.all())
    assert (
        mail.outbox[0].subject
        == "[testserver] WARNING: Permissions granted to Challenge Participants"
    )

    mail.outbox.clear()

    # Just saving shouldn't create an email
    phase = Phase.objects.get(pk=phase.pk)
    phase.save()

    # Turning off shouldn't create an email
    phase.give_algorithm_editors_job_view_permissions = False
    phase.save()

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_give_algorithm_editors_job_view_permissions_only_for_algorithm_phase():
    phase = PhaseFactory(
        submission_kind=Phase.SubmissionKindChoices.CSV,
        give_algorithm_editors_job_view_permissions=False,
    )

    phase.give_algorithm_editors_job_view_permissions = True

    with pytest.raises(ValidationError) as err:
        phase.full_clean()

    assert err.value.message_dict["__all__"] == [
        "Give Algorithm Editors Job View Permissions can only be enabled for Algorithm type phases"
    ]

    phase.submission_kind = Phase.SubmissionKindChoices.ALGORITHM
    phase.full_clean()


@pytest.mark.django_db
def test_parent_phase_choices():
    p1, p2, p3, p4, p5 = PhaseFactory.create_batch(
        5, challenge=ChallengeFactory()
    )
    p6 = PhaseFactory()

    for phase in [p1, p2, p3, p4, p6]:
        phase.submission_kind = SubmissionKindChoices.ALGORITHM
    p5.submission_kind = SubmissionKindChoices.CSV

    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    interface1 = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2, ci3])
    interface2 = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2, ci4])
    interface3 = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])

    for phase in [p1, p4, p5]:
        phase.algorithm_interfaces.set([interface1])
    p2.algorithm_interfaces.set([interface2])
    p3.algorithm_interfaces.set([interface3])

    for phase in [p1, p2, p3, p4, p5, p6]:
        phase.save()

    assert list(p1.parent_phase_choices) == [p4]


@pytest.mark.django_db
def test_parent_phase_choices_no_circular_dependency():
    p1, p2, p3, p4 = PhaseFactory.create_batch(
        4,
        challenge=ChallengeFactory(),
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])

    for phase in [p1, p2, p3, p4]:
        phase.algorithm_interfaces.set([interface])

    p1.parent = p2
    p2.parent = p3
    p3.parent = p4
    p1.save()
    p2.save()
    p3.save()

    assert set(p1.parent_phase_choices) == {p2, p3, p4}
    assert set(p2.parent_phase_choices) == {p3, p4}
    assert set(p3.parent_phase_choices) == {p4}
    assert set(p4.parent_phase_choices) == set()


@pytest.mark.django_db
def test_clean_parent_phase():
    p1, p2, p3, p4 = PhaseFactory.create_batch(4, challenge=ChallengeFactory())
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])

    for phase in [p1, p2, p3, p4]:
        phase.submission_kind = SubmissionKindChoices.ALGORITHM
        phase.algorithm_interfaces.set([interface])
        phase.save()

    ai = ArchiveItemFactory()
    ai.values.add(ComponentInterfaceValueFactory(interface=ci1))
    p1.archive = ai.archive
    p2.archive = ai.archive
    p4.archive = ai.archive
    p4.submissions_open_at = now()
    p1.submissions_open_at = now() - timedelta(days=1)
    p1.save()
    p2.save()
    p4.save()

    p1.parent = p3
    with pytest.raises(ValidationError) as e:
        p1.clean()
    assert (
        "The parent phase needs to have at least 1 valid archive item."
        in str(e)
    )

    p1.parent = p4
    with pytest.raises(ValidationError) as e:
        p1.clean()
    assert SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT in str(e)

    p1.parent = p2
    p1.clean()


@pytest.mark.django_db
def test_read_only_fields_for_dependent_phases():
    p1 = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM,
        challenge=ChallengeFactory(),
    )
    p2 = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV, challenge=ChallengeFactory()
    )
    assert p1.read_only_fields_for_dependent_phases == [
        "submission_kind",
    ]
    assert p2.read_only_fields_for_dependent_phases == ["submission_kind"]


@pytest.mark.django_db
def test_external_evaluation_validation():
    phase = PhaseFactory(external_evaluation=True)
    MethodFactory(phase=phase)

    with pytest.raises(ValidationError) as e:
        phase._clean_external_evaluation()
    assert (
        "Phases that have an evaluation method cannot be turned into external evaluation phases. Remove the method and try again."
        in str(e)
    )

    Method.objects.all().delete()

    with pytest.raises(ValidationError) as e:
        phase._clean_external_evaluation()
    assert (
        "External evaluation is only possible for algorithm submission phases."
        in str(e)
    )

    phase.submission_kind = SubmissionKindChoices.ALGORITHM
    phase.save()

    with pytest.raises(ValidationError) as e:
        phase._clean_external_evaluation()
    assert "An external evaluation phase must have a parent phase." in str(e)

    phase.parent = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM
    )
    phase.save()

    phase._clean_external_evaluation()


@pytest.mark.django_db
def test_is_evaluated_with_active_image_and_ground_truth():
    phase = PhaseFactory()
    s = SubmissionFactory(phase=phase)
    EvaluationFactory(submission=s, time_limit=phase.evaluation_time_limit)
    assert s.is_evaluated_with_active_image_and_ground_truth

    # add a method
    MethodFactory(
        phase=phase,
        is_in_registry=True,
        is_manifest_valid=True,
        is_desired_version=True,
    )
    del phase.active_image
    del s.is_evaluated_with_active_image_and_ground_truth
    assert not s.is_evaluated_with_active_image_and_ground_truth

    EvaluationFactory(
        submission=s,
        method=phase.active_image,
        time_limit=phase.evaluation_time_limit,
    )
    del s.is_evaluated_with_active_image_and_ground_truth
    assert s.is_evaluated_with_active_image_and_ground_truth

    # add a ground truth
    gt = EvaluationGroundTruthFactory(phase=phase, is_desired_version=True)
    del phase.active_ground_truth
    del s.is_evaluated_with_active_image_and_ground_truth
    assert not s.is_evaluated_with_active_image_and_ground_truth

    EvaluationFactory(
        submission=s,
        method=phase.active_image,
        ground_truth=phase.active_ground_truth,
        time_limit=phase.evaluation_time_limit,
    )
    del s.is_evaluated_with_active_image_and_ground_truth
    assert s.is_evaluated_with_active_image_and_ground_truth

    # remove ground truth and also add another evaluation with another ground truth
    gt.is_desired_version = False
    gt.save()
    gt2 = EvaluationGroundTruthFactory(phase=phase, is_desired_version=False)
    EvaluationFactory(
        submission=s,
        method=phase.active_image,
        ground_truth=gt2,
        time_limit=phase.evaluation_time_limit,
    )
    del phase.active_ground_truth
    del s.is_evaluated_with_active_image_and_ground_truth
    assert s.is_evaluated_with_active_image_and_ground_truth


@pytest.mark.django_db
class TestInputsComplete:
    def test_inputs_complete_for_prediction_submission(self):
        eval_pred = EvaluationFactory(
            submission__predictions_file=None, time_limit=10
        )
        assert not eval_pred.inputs_complete

        eval_pred2 = EvaluationFactory(time_limit=10)
        assert eval_pred2.inputs_complete

    def test_non_successful_jobs_ignored(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_inputs_complete_for_algorithm_submission_without_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        # no need to set outputs, we assume that only a job with valid outputs has a
        # status of SUCCESS

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert eval_alg.inputs_complete

    def test_inputs_complete_for_algorithm_submission_with_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        algorithm_model = AlgorithmModelFactory(
            algorithm=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm
        )
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=algorithm_model,
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=algorithm_model,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=algorithm_model,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert eval_alg.inputs_complete

    def test_jobs_with_creator_ignored(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=archive_items_and_jobs_for_interfaces.algorithm_image.creator,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=archive_items_and_jobs_for_interfaces.algorithm_image.creator,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_jobs_with_other_inputs_ignored(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        # now also create jobs with other inputs, those should be ignored
        j5, j6 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j5.inputs.set(
            [
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface1.inputs.get()
                )
            ]
        )
        j6.inputs.set(
            [
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface1.inputs.get()
                )
            ]
        )

        # create 2 jobs per interface, for each of the archive items
        j7, j8 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j7.inputs.set(
            [
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface2.inputs.first()
                ),
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface2.inputs.last()
                ),
            ]
        )
        j8.inputs.set(
            [
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface2.inputs.first()
                ),
                ComponentInterfaceValueFactory(
                    interface=archive_items_and_jobs_for_interfaces.interface2.inputs.last()
                ),
            ]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert eval_alg.inputs_complete

    def test_jobs_with_partial_inputs_ignored(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 complete jobs for interface1
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create jobs for interface 2 with only part of the required inputs,
        # those should not count as complete jobs
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface2[0][0]]
        )
        j4.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface2[1][1]]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_jobs_with_different_image_ignored_for_submission_without_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=AlgorithmImageFactory(),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=AlgorithmImageFactory(),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_successful_job_with_model_ignored_for_submission_without_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=AlgorithmModelFactory(),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=AlgorithmModelFactory(),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_jobs_with_different_model_ignored_for_submission_with_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        algorithm_model = AlgorithmModelFactory(
            algorithm=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm
        )
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=algorithm_model,
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=AlgorithmModelFactory(
                algorithm=eval_alg.submission.algorithm_image.algorithm
            ),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=AlgorithmModelFactory(
                algorithm=eval_alg.submission.algorithm_image.algorithm
            ),
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete

    def test_jobs_without_model_ignored_for_submission_with_model(
        self, archive_items_and_jobs_for_interfaces
    ):
        algorithm_model = AlgorithmModelFactory(
            algorithm=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm
        )
        submission = SubmissionFactory(
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_model=algorithm_model,
        )
        submission.phase.archive = (
            archive_items_and_jobs_for_interfaces.archive
        )
        submission.phase.save()
        submission.phase.algorithm_interfaces.set(
            [
                archive_items_and_jobs_for_interfaces.interface1,
                archive_items_and_jobs_for_interfaces.interface2,
            ]
        )

        eval_alg = EvaluationFactory(submission=submission, time_limit=10)
        assert not eval_alg.inputs_complete

        # create 2 jobs per interface, for each of the archive items
        j1, j2 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface1,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j1.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[0]]
        )
        j2.inputs.set(
            [archive_items_and_jobs_for_interfaces.civs_for_interface1[1]]
        )

        # create 2 jobs per interface, for each of the archive items
        j3, j4 = AlgorithmJobFactory.create_batch(
            2,
            status=Job.SUCCESS,
            creator=None,
            algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
            algorithm_interface=archive_items_and_jobs_for_interfaces.interface2,
            time_limit=archive_items_and_jobs_for_interfaces.algorithm_image.algorithm.time_limit,
        )
        j3.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[0]
        )
        j4.inputs.set(
            archive_items_and_jobs_for_interfaces.civs_for_interface2[1]
        )

        del eval_alg.successful_jobs_per_interface
        del eval_alg.successful_job_count_per_interface
        del eval_alg.total_successful_jobs
        del eval_alg.inputs_complete
        assert not eval_alg.inputs_complete


@pytest.mark.django_db
def test_algorithm_requires_gpu_unchangable():
    submission = SubmissionFactory()

    submission.algorithm_requires_gpu_type = GPUTypeChoices.T4

    with pytest.raises(ValueError) as error:
        submission.save()

    assert "requires_gpu_type cannot be changed" in str(error)


@pytest.mark.django_db
def test_algorithm_requires_memory_unchangable():
    submission = SubmissionFactory()

    submission.algorithm_requires_memory_gb = 500

    with pytest.raises(ValueError) as error:
        submission.save()

    assert "algorithm_requires_memory_gb cannot be changed" in str(error)


@pytest.mark.django_db
def test_archive_item_matching_to_interfaces():
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

    i1, i2, i3, i4 = ArchiveItemFactory.create_batch(4, archive=archive)

    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    interface1 = AlgorithmInterfaceFactory(inputs=[ci1])
    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci2])
    interface3 = AlgorithmInterfaceFactory(inputs=[ci2, ci3, ci4])

    i1.values.add(
        ComponentInterfaceValueFactory(interface=ci1)
    )  # Valid for interface 1
    i2.values.set(
        [
            ComponentInterfaceValueFactory(interface=ci1),
            ComponentInterfaceValueFactory(interface=ci2),
        ]
    )  # valid for interface 2
    i3.values.set(
        [
            ComponentInterfaceValueFactory(interface=ci1),
            ComponentInterfaceValueFactory(
                interface=ComponentInterfaceFactory()
            ),
        ]
    )  # valid for no interface, because of additional / mismatching interface
    i4.values.set(
        [
            ComponentInterfaceValueFactory(interface=ci2),
            ComponentInterfaceValueFactory(
                interface=ComponentInterfaceFactory()
            ),
        ]
    )  # valid for no interface, because of additional / mismatching interface

    phase.algorithm_interfaces.set([interface1])
    assert phase.valid_archive_items_per_interface.keys() == {interface1}
    assert phase.valid_archive_items_per_interface[interface1].get() == i1
    assert phase.valid_archive_item_count_per_interface == {interface1: 1}
    assert phase.jobs_to_schedule_per_submission == 1

    del phase.valid_archive_items_per_interface
    del phase.valid_archive_item_count_per_interface
    del phase.jobs_to_schedule_per_submission
    phase.algorithm_interfaces.set([interface2])
    assert phase.valid_archive_items_per_interface.keys() == {interface2}
    assert phase.valid_archive_items_per_interface[interface2].get() == i2
    assert phase.valid_archive_item_count_per_interface == {interface2: 1}
    assert phase.jobs_to_schedule_per_submission == 1

    del phase.valid_archive_items_per_interface
    del phase.valid_archive_item_count_per_interface
    del phase.jobs_to_schedule_per_submission
    phase.algorithm_interfaces.set([interface3])
    assert phase.valid_archive_items_per_interface.keys() == {interface3}
    assert not phase.valid_archive_items_per_interface[interface3].exists()
    assert phase.valid_archive_item_count_per_interface == {interface3: 0}
    assert phase.jobs_to_schedule_per_submission == 0

    del phase.valid_archive_items_per_interface
    del phase.valid_archive_item_count_per_interface
    del phase.jobs_to_schedule_per_submission
    phase.algorithm_interfaces.set([interface1, interface3])
    assert phase.valid_archive_items_per_interface.keys() == {
        interface1,
        interface3,
    }
    assert phase.valid_archive_items_per_interface[interface1].get() == i1
    assert not phase.valid_archive_items_per_interface[interface3].exists()
    assert phase.valid_archive_item_count_per_interface == {
        interface1: 1,
        interface3: 0,
    }
    assert phase.jobs_to_schedule_per_submission == 1

    del phase.valid_archive_items_per_interface
    del phase.valid_archive_item_count_per_interface
    del phase.jobs_to_schedule_per_submission
    phase.algorithm_interfaces.set([interface1, interface2, interface3])
    assert phase.valid_archive_items_per_interface.keys() == {
        interface1,
        interface2,
        interface3,
    }
    assert phase.valid_archive_items_per_interface[interface1].get() == i1
    assert phase.valid_archive_items_per_interface[interface2].get() == i2
    assert not phase.valid_archive_items_per_interface[interface3].exists()
    assert phase.valid_archive_item_count_per_interface == {
        interface1: 1,
        interface2: 1,
        interface3: 0,
    }
    assert phase.jobs_to_schedule_per_submission == 2


@pytest.mark.django_db
def test_get_valid_jobs_for_interfaces_and_archive_items(
    archive_items_and_jobs_for_interfaces,
):

    valid_job_inputs = get_archive_items_for_interfaces(
        algorithm_interfaces=[
            archive_items_and_jobs_for_interfaces.interface1,
            archive_items_and_jobs_for_interfaces.interface2,
        ],
        archive_items=ArchiveItem.objects.all(),
    )

    jobs_per_interface = get_valid_jobs_for_interfaces_and_archive_items(
        algorithm_interfaces=[
            archive_items_and_jobs_for_interfaces.interface1,
            archive_items_and_jobs_for_interfaces.interface2,
        ],
        algorithm_image=archive_items_and_jobs_for_interfaces.algorithm_image,
        valid_archive_items_per_interface=valid_job_inputs,
    )
    assert jobs_per_interface == {
        archive_items_and_jobs_for_interfaces.interface1: [
            archive_items_and_jobs_for_interfaces.jobs_for_interface1[0]
        ],
        archive_items_and_jobs_for_interfaces.interface2: [
            archive_items_and_jobs_for_interfaces.jobs_for_interface2[0]
        ],
    }


@pytest.mark.django_db
def test_additional_inputs_complete():
    phase = PhaseFactory()
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    phase.additional_evaluation_inputs.set([ci1, ci2])

    civ1 = ComponentInterfaceValueFactory(interface=ci1)
    civ2 = ComponentInterfaceValueFactory(interface=ci2)
    civ3 = ComponentInterfaceValueFactory(interface=ci3)
    civ4 = ComponentInterfaceValueFactory(interface=ci3)

    eval = EvaluationFactory(submission__phase=phase, time_limit=10)

    assert not eval.additional_inputs_complete

    # add required inputs
    eval.inputs.set([civ1, civ2])
    del eval.additional_inputs_complete
    assert eval.additional_inputs_complete

    # it should not matter if other inputs are present as well
    eval.inputs.set([civ1, civ2, civ3])
    del eval.additional_inputs_complete
    assert eval.additional_inputs_complete

    # or if multiple inputs of the same type are present
    eval.inputs.set([civ1, civ2, civ3, civ4])
    del eval.additional_inputs_complete
    assert eval.additional_inputs_complete


class PhaseWithInputsAndCIVs(NamedTuple):
    phase: PhaseFactory
    civs: [ComponentInterfaceValueFactory]


@pytest.fixture
def phase_with_image_and_gt_and_two_inputs():
    phase = PhaseFactory()
    MethodFactory(
        phase=phase,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    EvaluationGroundTruthFactory(phase=phase, is_desired_version=True)
    editor = UserFactory()
    phase.challenge.add_admin(editor)

    ci1, ci2 = ComponentInterfaceFactory.create_batch(
        2, kind=ComponentInterface.Kind.STRING
    )
    phase.additional_evaluation_inputs.set([ci1, ci2])

    civs = [
        ComponentInterfaceValueFactory(interface=ci1, value="foo"),
        ComponentInterfaceValueFactory(interface=ci2, value="bar"),
    ]

    return PhaseWithInputsAndCIVs(
        phase=phase,
        civs=civs,
    )


@pytest.mark.django_db
class TestGetEvaluationsWithSameInputs:

    def get_civ_data(self, civs):
        return [
            CIVData(interface_slug=civ.interface.slug, value=civ.value)
            for civ in civs
        ]

    def test_evaluation_with_same_method_different_gt(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=EvaluationGroundTruthFactory(),  # new
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 0

    def test_job_with_same_gt_different_method(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=MethodFactory(),  # new
            submission=submission,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 0

    def test_job_with_same_gt_and_method(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 1
        assert eval in evals

    def test_job_with_different_method_and_gt(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=MethodFactory(),  # new
            submission=submission,
            ground_truth=EvaluationGroundTruthFactory(),  # new
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 0

    def test_eval_with_same_method_no_gt_provided(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            ground_truth=phase.active_ground_truth,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=None,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 0

    def test_job_with_same_method_and_without_gt(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(civs)

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=None,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert eval in evals
        assert len(evals) == 1

    def test_eval_with_different_input(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        eval.inputs.set(
            [
                ComponentInterfaceValueFactory(),
                ComponentInterfaceValueFactory(),
            ]
        )

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=None,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        assert len(evals) == 0

    def test_eval_with_partially_overlapping_input(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        civs = phase_with_image_and_gt_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        # this eval should be ignored since it has incomplete inputs
        eval.inputs.set(
            [
                civs[0],
                ComponentInterfaceValueFactory(),
            ]
        )

        eval2 = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        # this eval should count since it has inputs for all configured additional inputs
        # it doesn't matter that there is also a third input
        eval2.inputs.set(
            [
                civs[0],
                civs[1],
                ComponentInterfaceValueFactory(),
            ]
        )

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=data,
            method=phase.active_image,
            submission=submission,
            ground_truth=None,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )

        assert len(evals) == 1
        assert eval2 in evals

    def test_eval_without_inputs_configured(
        self, phase_with_image_and_gt_and_two_inputs
    ):
        phase = phase_with_image_and_gt_and_two_inputs.phase
        # remove inputs
        phase.additional_evaluation_inputs.clear()

        civs = phase_with_image_and_gt_and_two_inputs.civs
        submission = SubmissionFactory(
            phase=phase, algorithm_image=AlgorithmImageFactory()
        )

        eval = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )
        # this eval should count since it only has inputs that are
        # not configured for the phase
        eval.inputs.set(
            [
                civs[0],
                civs[1],
            ]
        )

        # this eval should count since it has no inputs, but matches otherwise
        eval2 = EvaluationFactory(
            submission=submission,
            method=phase.active_image,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )

        evals = Evaluation.objects.get_evaluations_with_same_inputs(
            inputs=[],
            method=phase.active_image,
            submission=submission,
            ground_truth=None,
            time_limit=phase.evaluation_time_limit,
            requires_gpu_type=phase.evaluation_requires_gpu_type,
            requires_memory_gb=phase.evaluation_requires_memory_gb,
        )

        assert len(evals) == 2
        assert eval in evals
        assert eval2 in evals


@pytest.mark.django_db
def test_disjoint_inputs_and_algorithm_sockets():
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    phase.algorithm_interfaces.set([interface])

    for ci in [ci1, ci2]:
        instance = PhaseAdditionalEvaluationInput(socket=ci, phase=phase)
        with pytest.raises(ValidationError) as e:
            instance.clean()
        assert (
            f"{ci.slug} cannot be defined as evaluation inputs or "
            "outputs because it is already defined as algorithm input or "
            "output for this phase" in str(e)
        )

    for ci in [ci3, ci4]:
        instance = PhaseAdditionalEvaluationInput(
            socket=ci, phase=PhaseFactory()
        )
        with nullcontext():
            instance.clean()


@pytest.mark.parametrize("slug", RESERVED_SOCKET_SLUGS)
@pytest.mark.django_db
def test_non_evaluation_socket_slugs(slug):
    ci, _ = ComponentInterface.objects.get_or_create(slug=slug)

    instance = PhaseAdditionalEvaluationInput(socket=ci, phase=PhaseFactory())
    with pytest.raises(ValidationError) as e:
        instance.clean()
    assert (
        "Evaluation inputs cannot be of the following types: predictions-csv-file, predictions-json-file, predictions-zip-file, metrics-json-file, results-json-file"
        in str(e)
    )


@pytest.mark.django_db
def test_phase_submission_kind_change():
    # Initial create with submission kind is OK
    phase = PhaseFactory(submission_kind=Phase.SubmissionKindChoices.ALGORITHM)

    # Can change when no submissions exist
    phase.submission_kind = Phase.SubmissionKindChoices.CSV
    phase.full_clean()

    # Cannot change when submission exists
    submission = SubmissionFactory(phase=phase)
    with pytest.raises(ValidationError):
        phase.full_clean()

    # Can change again after removing submission
    submission.delete()
    phase.full_clean()


@pytest.mark.django_db
def test_method_cannot_be_added_to_external_phase():
    phase = PhaseFactory(external_evaluation=True)

    method = MethodFactory(phase=phase)

    with pytest.raises(ValidationError) as e:
        method.full_clean()

    assert "You cannot add a method to an external evaluation." in str(e)
