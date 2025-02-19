import pytest
from django.contrib.auth.models import Group
from django.core import mail

from tests.factories import ChallengeRequestFactory, UserFactory


@pytest.mark.django_db
def test_only_reviewers_sent_email(settings):
    reviewer = UserFactory()

    Group.objects.get(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    ).user_set.add(reviewer)

    request = ChallengeRequestFactory()

    assert len(mail.outbox) == 2

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
