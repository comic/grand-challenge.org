from collections import namedtuple
from datetime import timedelta
from itertools import chain

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.timezone import now

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.models import (
    SUBMISSION_WINDOW_PARENT_VALIDATION_TEXT,
    CombinedLeaderboard,
    Evaluation,
    Phase,
)
from grandchallenge.evaluation.tasks import (
    calculate_ranks,
    create_evaluation,
    update_combined_leaderboard,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentStatusChoices
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    CombinedLeaderboardFactory,
    EvaluationFactory,
    GroundTruthFactory,
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

    interface = ComponentInterfaceFactory()
    algorithm_image.algorithm.inputs.set([interface])

    images = ImageFactory.create_batch(3)

    for image in images[:2]:
        civ = ComponentInterfaceValueFactory(image=image, interface=interface)
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

    with django_capture_on_commit_callbacks() as callbacks:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    # Execute the callbacks non-recursively
    for c in callbacks:
        c()

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

    with django_capture_on_commit_callbacks(execute=False) as callbacks1:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    with django_capture_on_commit_callbacks(execute=False) as callbacks2:
        create_evaluation(submission_pk=s.pk, max_initial_jobs=None)

    # Execute the callbacks non-recursively
    for c in chain(callbacks1, callbacks2):
        c()

    assert Job.objects.count() == 2


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
        create_evaluation(submission_pk=sub.pk, max_initial_jobs=None)

    assert Evaluation.objects.count() == 1

    gt = GroundTruthFactory(phase=sub.phase, is_desired_version=True)
    assert sub.phase.active_ground_truth == gt

    with django_capture_on_commit_callbacks(execute=True):
        create_evaluation(submission_pk=sub.pk, max_initial_jobs=None)

    assert Evaluation.objects.count() == 2

    m = MethodFactory(
        phase=sub.phase, is_in_registry=True, is_manifest_valid=True
    )
    m.mark_desired_version()
    assert sub.phase.active_image == m

    with django_capture_on_commit_callbacks(execute=True):
        create_evaluation(submission_pk=sub.pk, max_initial_jobs=None)

    assert Evaluation.objects.count() == 3

    with django_capture_on_commit_callbacks(execute=True):
        create_evaluation(submission_pk=sub.pk, max_initial_jobs=None)

    assert Evaluation.objects.count() == 3


@pytest.mark.django_db
class TestPhaseLimits:
    def setup_method(self):
        phase = PhaseFactory()

        InvoiceFactory(
            challenge=phase.challenge,
            compute_costs_euros=10,
            payment_status=PaymentStatusChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        self.phase = Phase.objects.get(pk=phase.pk)
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
    phase = PhaseFactory()
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
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
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


@pytest.mark.django_db
def test_count_valid_archive_items():
    archive = ArchiveFactory()
    phase = PhaseFactory(archive=archive)
    i1, i2, i3 = ComponentInterfaceFactory.create_batch(3)

    phase.algorithm_inputs.set([i1, i2])

    # Valid archive item
    ai1 = ArchiveItemFactory(archive=archive)
    ai1.values.add(ComponentInterfaceValueFactory(interface=i1))
    ai1.values.add(ComponentInterfaceValueFactory(interface=i2))

    # Valid, but with extra value
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

    cciv1 = ComponentInterfaceValueFactory(interface=i1)
    cciv2 = ComponentInterfaceValueFactory(interface=i2)

    # Valid, reusing interfaces
    ai6 = ArchiveItemFactory(archive=archive)
    ai6.values.set([cciv1, cciv2])
    ai7 = ArchiveItemFactory(archive=archive)
    ai7.values.set([cciv1, cciv2])

    assert {*phase.valid_archive_items} == {ai1, ai2, ai6, ai7}


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
        creator_must_be_verified=True,
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

    for phase in [p1, p2, p3, p4, p5, p6]:
        phase.algorithm_inputs.set([ci1])

    for phase in [p1, p4, p5]:
        phase.algorithm_outputs.set([ci2, ci3])
    p2.algorithm_outputs.set([ci2, ci4])
    p3.algorithm_outputs.set([ci2])

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

    for phase in [p1, p2, p3, p4]:
        phase.algorithm_inputs.set([ci1])
        phase.algorithm_outputs.set([ci2])

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
    p1, p2, p3, p4 = PhaseFactory.create_batch(
        4, challenge=ChallengeFactory(), creator_must_be_verified=True
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)

    for phase in [p1, p2, p3, p4]:
        phase.submission_kind = SubmissionKindChoices.ALGORITHM
        phase.algorithm_inputs.set([ci1])
        phase.algorithm_outputs.set([ci2])
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
        "algorithm_inputs",
        "algorithm_outputs",
    ]
    assert p2.read_only_fields_for_dependent_phases == ["submission_kind"]
