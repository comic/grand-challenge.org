from datetime import datetime, timedelta

import pytest
from django.core import mail

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.challenges.tasks import (
    send_onboarding_task_reminder_emails,
    update_challenge_results_cache,
    update_compute_costs_and_storage_size,
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


def test_challenge_request_budget_calculation(settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"
    challenge_request = ChallengeRequest(
        expected_number_of_teams=10,
        inference_time_limit_in_minutes=10,
        average_size_of_test_image_in_mb=100,
        phase_1_number_of_submissions_per_team=10,
        phase_2_number_of_submissions_per_team=100,
        phase_1_number_of_test_images=100,
        phase_2_number_of_test_images=500,
        number_of_tasks=1,
    )

    assert challenge_request.budget == {
        "Data storage cost for phase 1": 10,
        "Compute costs for phase 1": 1960,
        "Total phase 1": 1970,
        "Data storage cost for phase 2": 40,
        "Compute costs for phase 2": 97910,
        "Total phase 2": 97950,
        "Docker storage cost": 4440,
        "Total across phases": 104360,
    }

    assert (
        challenge_request.budget["Total phase 2"]
        == challenge_request.budget["Data storage cost for phase 2"]
        + challenge_request.budget["Compute costs for phase 2"]
    )
    assert (
        challenge_request.budget["Total phase 1"]
        == challenge_request.budget["Data storage cost for phase 1"]
        + challenge_request.budget["Compute costs for phase 1"]
    )
    assert (
        challenge_request.budget["Total across phases"]
        == challenge_request.budget["Total phase 1"]
        + challenge_request.budget["Total phase 2"]
        + challenge_request.budget["Docker storage cost"]
    )

    challenge_request.number_of_tasks = 2

    del challenge_request.budget

    assert challenge_request.budget == {
        "Data storage cost for phase 1": 20,
        "Compute costs for phase 1": 3920,
        "Total phase 1": 3940,
        "Data storage cost for phase 2": 70,
        "Compute costs for phase 2": 195820,
        "Total phase 2": 195890,
        "Docker storage cost": 8880,
        "Total across phases": 208710,
    }

    assert (
        challenge_request.budget["Total phase 2"]
        == challenge_request.budget["Data storage cost for phase 2"]
        + challenge_request.budget["Compute costs for phase 2"]
    )
    assert (
        challenge_request.budget["Total phase 1"]
        == challenge_request.budget["Data storage cost for phase 1"]
        + challenge_request.budget["Compute costs for phase 1"]
    )
    assert (
        challenge_request.budget["Total across phases"]
        == challenge_request.budget["Total phase 1"]
        + challenge_request.budget["Total phase 2"]
        + challenge_request.budget["Docker storage cost"]
    )


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
    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=500000,
        time_limit=60,
    )
    update_compute_costs_and_storage_size()

    # Budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=300000,
        time_limit=60,
    )
    update_compute_costs_and_storage_size()

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
    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=100000,
        time_limit=60,
    )
    update_compute_costs_and_storage_size()

    # Next budget alert threshold not exceeded
    assert len(mail.outbox) == 0

    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=1,
        time_limit=60,
    )
    update_compute_costs_and_storage_size()

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
    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=950000,
        time_limit=60,
    )
    update_compute_costs_and_storage_size()

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
    EvaluationFactory(
        submission__phase=phase,
        compute_cost_euro_millicents=1,
        time_limit=60,
    )
    assert len(mail.outbox) == 0
    update_compute_costs_and_storage_size()
    assert len(mail.outbox) != 0
    assert "Budget Consumed Alert" in mail.outbox[0].subject


_mock_now = datetime(2025, 1, 29, 11, 0, 0)


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
                    deadline=_mock_now + timedelta(hours=24),
                ),
            ],
            None,
            None,
        ),
        (  # Case: one organizer overdue task
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                    deadline=_mock_now - timedelta(hours=24),
                ),
            ],
            "[{short_name}] 1 Organizer Onboarding Task Overdue",
            "[{short_name}] Action Required: 1 Onboarding Task Overdue",
        ),
        (
            # Case: organizer soon overdue
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                    deadline=_mock_now + timedelta(minutes=30),
                ),
            ],
            None,
            "[{short_name}] Reminder: 1 Onboarding Task Soon Due",
        ),
        (  # Case: support overdue task
            [
                dict(
                    responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
                    deadline=_mock_now - timedelta(hours=24),
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
    settings.CHALLENGE_ONBOARDING_TASKS_OVERDUE_SOON_CUTOFF = timedelta(
        hours=1
    )
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

    with mocker.patch(
        "grandchallenge.challenges.models.now", return_value=_mock_now
    ):
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

    for m in mail.outbox:
        print("Subject: ", m.subject)
        print(m.body)
