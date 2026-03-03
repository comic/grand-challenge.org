import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.utils.timezone import now

from grandchallenge.challenges.models import Challenge, ChallengeRequest
from tests.factories import ChallengeRequestFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_challenge_request_submitted_sent_email(settings):
    reviewer = UserFactory()

    Group.objects.get(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    ).user_set.add(reviewer)

    request = ChallengeRequestFactory()
    request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )  # Submit it
    request.save()

    assert len(mail.outbox) == 2, [m.subject for m in mail.outbox]

    reviewer_mail = [
        email
        for email in mail.outbox
        if email.recipients() == [reviewer.email]
    ]
    assert len(reviewer_mail) == 1
    assert reviewer_mail[0].subject == "[testserver] New Challenge Requested"

    creator_mail = [
        email
        for email in mail.outbox
        if email.recipients() == [request.creator.email]
    ]
    assert len(creator_mail) == 1
    assert (
        "Challenge Request Submitted Successfully" in creator_mail[0].subject
    )


@pytest.mark.django_db
def test_challenge_request_rejected_sent_email(client, challenge_reviewer):
    request = ChallengeRequestFactory(
        status=ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
        submitted=now(),
    )
    mail.outbox.clear()

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": request.pk},
        user=challenge_reviewer,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.REJECTED
        },
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].recipients() == [request.creator.email]
    assert (
        "We are very sorry to have to inform you that we will not be able to host your challenge on our platform"
        in mail.outbox[0].body
    )
    assert Challenge.objects.count() == 0


@pytest.mark.django_db
def test_challenge_request_accepted_sent_email_challenge_creation(
    client, challenge_reviewer
):
    request = ChallengeRequestFactory(
        status=ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
        submitted=now(),
    )
    mail.outbox.clear()

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-status-update",
        reverse_kwargs={"pk": request.pk},
        user=challenge_reviewer,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
        },
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].recipients() == [request.creator.email]
    assert (
        "We are happy to inform you that your challenge request has been accepted"
        in mail.outbox[0].body
    )
    assert Challenge.objects.count() == 1
    assert Challenge.objects.get().short_name == request.short_name
