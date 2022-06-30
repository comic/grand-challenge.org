import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from guardian.utils import get_anonymous_user

from grandchallenge.profiles.tasks import delete_users_who_dont_login
from tests.factories import UserFactory


@pytest.mark.django_db
def test_delete_users_who_dont_login(settings, client):
    settings.USER_LOGIN_TIMEOUT_DAYS = 0
    anon = get_anonymous_user()
    u1, u2 = UserFactory.create_batch(2)
    # u1 logs in and should not be deleted
    client.force_login(user=u1)

    assert {*get_user_model().objects.all()} == {anon, u1, u2}

    delete_users_who_dont_login()

    assert {*get_user_model().objects.all()} == {anon, u1}

    with pytest.raises(ObjectDoesNotExist):
        # u2 did not log in so was deleted
        u2.refresh_from_db()
