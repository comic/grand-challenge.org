from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.utils.timezone import datetime, timedelta

from grandchallenge.algorithms.models import Job
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.challenges.tasks import (
    send_challenge_request_draft_reminder_emails,
    send_onboarding_task_reminder_emails,
    update_challenge_compute_costs,
    update_challenge_results_cache,
)
from grandchallenge.utilization.models import JobWarmPoolUtilization
from grandchallenge.utilization.tasks import create_job_warm_pool_utilizations
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
from tests.invoices_tests.factories import InvoiceFactory


@pytest.mark.django_db
def test_challenge_update(two_challenge_sets, django_assert_num_queries):
    c1 = two_challenge_sets.challenge_set_1.challenge
    c2 = two_challenge_sets.challenge_set_2.challenge

    _ = EvaluationFactory(
        submission__phase__challenge=c1,
        method__phase__challenge=c1,
        time_limit=60,
    )
    _ = EvaluationFactory(
        submission__phase__challenge=c2,
        method__phase__challenge=c2,
        time_limit=60,
    )

    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()

    # check the # queries stays the same even with more challenges & evaluations

    c3 = ChallengeFactory()
    _ = EvaluationFactory(
        submission__phase__challenge=c3,
        method__phase__challenge=c3,
        time_limit=60,
    )
    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()


@pytest.mark.django_db
def test_challenge_creation_from_request():
    challenge_request = ChallengeRequestFactory()
    # an algorithm submission phase gets created
    challenge_request.create_challenge()
    assert Challenge.objects.count() == 1
    challenge = Challenge.objects.get()
    assert challenge.short_name == challenge_request.short_name
    # requester is admin of challenge
    assert challenge_request.creator in challenge.admins_group.user_set.all()


_fixed_now = datetime(2025, 1, 29, 11, 0, 0, tzinfo=ZoneInfo("UTC"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tasks_properties, staff_email_subject, challenge_organizer_email_subject",
    [
        (  # Case: no tasks
            [],
            None,
            None,
        ),
        (  # Case: task, but not overdue (Sanity)
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                    deadline=_fixed_now + timedelta(days=14),
                ),
            ],
            None,
            None,
        ),
        (  # Case: one organizer overdue task
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                    deadline=_fixed_now - timedelta(hours=24),
                ),
            ],
            "[{short_name}] Organizer Onboarding Tasks Overdue: 1",
            "[{short_name}] Action Required: 1 Onboarding Task Overdue",
        ),
        (
            # Case: organizer soon overdue
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                    deadline=_fixed_now + timedelta(minutes=30),
                ),
            ],
            None,
            "[{short_name}] Reminder: 1 Onboarding Task Soon Due",
        ),
        (  # Case: support overdue task
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
                    deadline=_fixed_now - timedelta(hours=24),
                ),
            ],
            "[{short_name}] Action required: 1 Support Onboarding Task Overdue",
            None,
        ),
    ],
)
def test_challenge_onboarding_task_due_emails(
    tasks_properties,
    staff_email_subject,
    challenge_organizer_email_subject,
    settings,
    mocker,
):
    challenge = ChallengeFactory()
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)

    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]

    for kwargs in tasks_properties:
        OnboardingTaskFactory(
            challenge=challenge,
            **kwargs,
        )

    mocker.patch(
        "grandchallenge.challenges.models.now",
        return_value=_fixed_now,
    )

    send_onboarding_task_reminder_emails()

    if staff_email_subject:
        staff_email = next(m for m in mail.outbox if staff_user.email in m.to)
        expected_subject = staff_email_subject.format(
            short_name=challenge.short_name
        )
        assert expected_subject in staff_email.subject
    else:
        assert not any(staff_user.email in m.to for m in mail.outbox)

    if challenge_organizer_email_subject:
        organizer_mail = next(
            m for m in mail.outbox if challenge_admin.email in m.to
        )
        expected_subject = challenge_organizer_email_subject.format(
            short_name=challenge.short_name
        )
        assert expected_subject in organizer_mail.subject
    else:
        assert not any(challenge_admin.email in m.to for m in mail.outbox)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "description, created_offsets, expected_recipients_indices",
    [
        (
            "single valid request",
            [
                (
                    "Target",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
            ],
            [0],  # 1 email
        ),
        (
            "too young request",
            [
                (
                    "Too young",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(hours=1),
                    0,
                ),
            ],
            [],  # 0 emails
        ),
        (
            "too many reminders",
            [
                (
                    "Too many",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=15),
                    3,
                ),
            ],
            [],  # 0 emails
        ),
        (
            "wrong status request",
            [
                (
                    "Target",
                    ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
            ],
            [],  # 0 emails
        ),
        (
            "multiple valid requests",
            [
                (
                    "Target 1",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
                (
                    "Target 2",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
            ],
            [0, 1],  # 2 emails
        ),
        (
            "mix of valid and invalid",
            [
                (
                    "Valid",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
                (
                    "Too young",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(hours=1),
                    0,
                ),
                (
                    "Too many reminders",
                    ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
                    _fixed_now - timedelta(days=40),
                    3,
                ),
                (
                    "Wrong status",
                    ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
                    _fixed_now - timedelta(days=15),
                    0,
                ),
            ],
            [0],  # 1 email
        ),
    ],
)
def test_challenge_request_draft_reminder_emails(
    mocker, settings, description, created_offsets, expected_recipients_indices
):
    settings.CHALLENGE_REQUEST_AGE_START_DRAFT_REMINDER_CUTOFF = timedelta(
        days=7
    )
    settings.CHALLENGE_REQUEST_MAX_DRAFT_REMINDERS = 2

    mocker.patch(
        "grandchallenge.challenges.tasks.now",
        return_value=_fixed_now,
    )

    requests = []
    for title, status, fixed_created, reminders_sent in created_offsets:
        challenge_request = ChallengeRequestFactory(
            title=title,
            status=status,
            draft_reminder_count=reminders_sent,
        )
        challenge_request.created = fixed_created
        challenge_request.save()
        requests.append(challenge_request)

    mail.outbox.clear()

    send_challenge_request_draft_reminder_emails()

    expected_recipients = [
        requests[i].creator.email for i in expected_recipients_indices
    ]
    assert len(mail.outbox) == len(expected_recipients), description

    actual_recipients = {r for m in mail.outbox for r in m.recipients()}
    assert actual_recipients == set(expected_recipients)

    for i in expected_recipients_indices:
        user_emails = [
            m
            for m in mail.outbox
            if requests[i].creator.email in m.recipients()
        ]
        assert len(user_emails) == 1
        assert requests[i].title in user_emails[0].body


@pytest.mark.django_db
def test_update_challenge_compute_costs_no_utilization(
    settings, django_capture_on_commit_callbacks
):
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    invoice = InvoiceFactory(challenge=challenge)

    assert invoice.compute_cost_euro_millicents == 0

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    invoice.refresh_from_db()
    assert invoice.compute_cost_euro_millicents == 0


@pytest.mark.django_db
def test_update_challenge_compute_costs(
    settings, django_capture_on_commit_callbacks
):

    settings.COMPONENTS_DEFAULT_BACKEND = (
        "tests.utilization_tests.test_tasks.UtilizationExecutor"
    )
    settings.LAMBDA_TASKS_EAGER = True

    challenge = ChallengeFactory()
    invoice = InvoiceFactory(challenge=challenge)
    phase = PhaseFactory(challenge=challenge)

    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation_utilization = evaluation.evaluation_utilization
    evaluation_utilization.invoice = invoice
    evaluation_utilization.compute_cost_euro_millicents = 1
    evaluation_utilization.save()

    job = AlgorithmJobFactory(
        status=Job.SUCCESS,
        use_warm_pool=True,
        time_limit=60,
    )

    job_utilization = job.job_utilization
    job_utilization.phase = phase
    job_utilization.challenge = challenge
    job_utilization.invoice = invoice
    job_utilization.compute_cost_euro_millicents = 2
    job_utilization.save()

    job2 = AlgorithmJobFactory(
        status=Job.SUCCESS,
        use_warm_pool=True,
        time_limit=60,
    )

    job2_utilization = job2.job_utilization
    job2_utilization.phase = phase
    job2_utilization.challenge = challenge
    job2_utilization.invoice = invoice
    job2_utilization.compute_cost_euro_millicents = 4
    job2_utilization.save()

    assert not JobWarmPoolUtilization.objects.exists()
    create_job_warm_pool_utilizations()
    for job_warm_pool_utilization in JobWarmPoolUtilization.objects.all():
        job_warm_pool_utilization.compute_cost_euro_millicents = 8
        job_warm_pool_utilization.save()

    assert invoice.compute_cost_euro_millicents == 0

    with django_capture_on_commit_callbacks(execute=True):
        update_challenge_compute_costs()

    invoice.refresh_from_db()
    assert invoice.compute_cost_euro_millicents == 1 + 2 + 4 + 8 + 8


@pytest.mark.django_db
def test_challenge_request_draft_reminder_emails_increments_counter(
    mocker, settings
):
    settings.CHALLENGE_REQUEST_AGE_START_DRAFT_REMINDER_CUTOFF = timedelta(
        days=7
    )
    settings.CHALLENGE_REQUEST_MAX_DRAFT_REMINDERS = 2

    mocker.patch(
        "grandchallenge.challenges.tasks.now",
        return_value=_fixed_now,
    )

    challenge_request = ChallengeRequestFactory(
        title="Target",
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
        draft_reminder_count=1,
    )
    challenge_request.created = _fixed_now - timedelta(days=15)
    challenge_request.save()

    mail.outbox.clear()

    send_challenge_request_draft_reminder_emails()
    assert len(mail.outbox) == 1
    challenge_request.refresh_from_db()
    assert challenge_request.draft_reminder_count == 2
