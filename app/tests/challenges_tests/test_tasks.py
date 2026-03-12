from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.utils.timezone import datetime, timedelta

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
from grandchallenge.invoices.models import PaymentStatusChoices
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


@pytest.mark.django_db
def test_challenge_budget_alert_email(settings):
    challenge = ChallengeFactory(short_name="test")
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    phase = PhaseFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )

    evaluation.utilization.compute_cost_euro_millicents = 500000
    evaluation.utilization.save()
    update_challenge_compute_costs()

    # Budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.compute_cost_euro_millicents = 300000
    evaluation.utilization.save()
    update_challenge_compute_costs()

    # Budget alert threshold exceeded
    assert len(mail.outbox) == 3
    recipients = {r for m in mail.outbox for r in m.to}
    assert recipients == {
        challenge.creator.email,
        challenge_admin.email,
        staff_user.email,
    }

    challenge_admin_email = [
        m for m in mail.outbox if challenge_admin.email in m.to
    ]
    assert (
        challenge_admin_email[0].subject
        == "[testserver] [test] over 70% Budget Consumed Alert"
    )
    assert (
        "We would like to inform you that more than 70% of the compute budget for "
        "the test challenge has been used." in challenge_admin_email[0].body
    )

    mail.outbox.clear()
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.compute_cost_euro_millicents = 100000
    evaluation.utilization.save()
    update_challenge_compute_costs()

    # Next budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.compute_cost_euro_millicents = 1
    evaluation.utilization.save()
    update_challenge_compute_costs()

    # Next budget alert threshold exceeded
    assert len(mail.outbox) != 0
    assert (
        mail.outbox[0].subject
        == "[testserver] [test] over 90% Budget Consumed Alert"
    )


@pytest.mark.django_db
def test_challenge_budget_alert_two_thresholds_one_email(settings):
    challenge = ChallengeFactory(short_name="test")
    assert challenge.percent_budget_consumed_warning_thresholds == [
        70,
        90,
        100,
    ]
    challenge_admin = UserFactory()
    challenge.add_admin(challenge_admin)
    staff_user = UserFactory(is_staff=True)
    settings.MANAGERS = [(staff_user.last_name, staff_user.email)]
    InvoiceFactory(
        challenge=challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    phase = PhaseFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.compute_cost_euro_millicents = 950000
    evaluation.utilization.save()
    update_challenge_compute_costs()

    # Two budget alert thresholds exceeded, alert only sent for last one.
    assert len(mail.outbox) == 3
    recipients = {r for m in mail.outbox for r in m.to}
    assert recipients == {
        challenge.creator.email,
        challenge_admin.email,
        staff_user.email,
    }
    assert (
        mail.outbox[0].subject
        == "[testserver] [test] over 90% Budget Consumed Alert"
    )


@pytest.mark.django_db
def test_challenge_budget_alert_no_budget():
    challenge = ChallengeFactory()
    phase = PhaseFactory(challenge=challenge)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=60,
    )
    evaluation.utilization.compute_cost_euro_millicents = 1
    evaluation.utilization.save()
    assert len(mail.outbox) == 0
    update_challenge_compute_costs()
    assert len(mail.outbox) != 0
    assert "Budget Consumed Alert" in mail.outbox[0].subject


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
def test_challenge_request_draft_reminder_emails(mocker, settings):
    mocker.patch(
        "grandchallenge.challenges.tasks.now",
        return_value=_fixed_now,
    )

    target_challenge_request = ChallengeRequestFactory(
        title="Target",
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
    )
    target_challenge_request.created = (
        _fixed_now
        - settings.CHALLENGE_REQUEST_REMINDER_CUTOFF
        - timedelta(minutes=1)
    )
    target_challenge_request.save()

    # Create decoy challenge requests that should not trigger a reminder email
    too_young_challenge_request = ChallengeRequestFactory(
        title="Not old enough",
        short_name="test-challenge-not-old-enough",
        status=ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
    )
    too_young_challenge_request.created = _fixed_now
    too_young_challenge_request.save()

    for status in (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
        ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
        ChallengeRequest.ChallengeRequestStatusChoices.REJECTED,
    ):
        wrong_status_request = ChallengeRequestFactory(
            title=f"Wrong status {status}",
            short_name=f"test-challenge-{status}",
            status=status,
        )
        wrong_status_request.created = target_challenge_request.created
        wrong_status_request.save()

    mail.outbox.clear()

    send_challenge_request_draft_reminder_emails()

    assert len(mail.outbox) == 1, [m.subject for m in mail.outbox]
    email = mail.outbox[0]

    assert email.recipients() == [target_challenge_request.creator.email]
    assert target_challenge_request.title in email.body
