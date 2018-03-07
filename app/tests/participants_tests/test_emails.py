import pytest
from django.core import mail

from comicmodels.models import RegistrationRequest
from comicsite.core.urlresolvers import reverse
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_new_registration_email(client, ChallengeSet):
    user = UserFactory()

    response = get_view_for_user(
        viewname='participants:registration-create',
        client=client,
        method=client.post,
        user=user,
        challenge=ChallengeSet.challenge,
    )

    assert response.status_code == 302

    email = mail.outbox[-1]

    RegistrationRequest.objects.get(user=user, project=ChallengeSet.challenge)

    approval_link = reverse('participants:registration-list',
                            args=[ChallengeSet.challenge.short_name])

    assert ChallengeSet.admin.email in email.to
    assert 'New participation request' in email.subject
    assert ChallengeSet.challenge.short_name in email.subject
    assert approval_link in email.alternatives[0][0]
