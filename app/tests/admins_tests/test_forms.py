import pytest
from django.core import mail

from grandchallenge.admins.forms import AdminsForm
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_admins_add(client, two_challenge_sets):
    user = UserFactory()
    assert not two_challenge_sets.challenge_set_1.challenge.is_admin(user=user)
    assert not two_challenge_sets.challenge_set_2.challenge.is_admin(user=user)
    response = get_view_for_user(
        viewname="admins:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        data={"user": user.pk, "action": AdminsForm.ADD},
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert response.status_code == 302
    email = mail.outbox[-1]
    assert (
        two_challenge_sets.challenge_set_1.challenge.short_name
        in email.subject
    )
    assert user.email in email.to
    assert two_challenge_sets.challenge_set_1.challenge.is_admin(user=user)
    assert not two_challenge_sets.challenge_set_2.challenge.is_admin(user=user)


@pytest.mark.django_db
def test_admins_remove(client, two_challenge_sets):
    assert two_challenge_sets.challenge_set_1.challenge.is_admin(
        user=two_challenge_sets.admin12
    )
    assert two_challenge_sets.challenge_set_2.challenge.is_admin(
        user=two_challenge_sets.admin12
    )
    response = get_view_for_user(
        viewname="admins:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        data={
            "user": two_challenge_sets.admin12.pk,
            "action": AdminsForm.REMOVE,
        },
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert response.status_code == 302
    assert not two_challenge_sets.challenge_set_1.challenge.is_admin(
        user=two_challenge_sets.admin12
    )
    assert two_challenge_sets.challenge_set_2.challenge.is_admin(
        user=two_challenge_sets.admin12
    )
