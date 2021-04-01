import pytest
from django.conf import settings
from django.urls import reverse

from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_logged_in_view(client):
    viewname = "notifications:list"
    response = get_view_for_user(client=client, viewname=viewname, user=None)

    assert response.status_code == 302
    assert response.url == f"{settings.LOGIN_URL}?next={reverse(viewname)}"


@pytest.mark.django_db
def test_last_read_updated(client):
    viewname = "notifications:list"
    u = UserFactory()

    assert u.user_profile.notifications_last_read_at is None

    response = get_view_for_user(client=client, viewname=viewname, user=u)
    assert response.status_code == 200

    u.user_profile.refresh_from_db()
    assert u.user_profile.notifications_last_read_at is not None
