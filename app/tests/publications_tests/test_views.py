import pytest
from django.contrib.auth.models import Group
from guardian.utils import get_anonymous_user

from config import settings
from grandchallenge.publications.models import Publication
from tests.factories import UserFactory
from tests.utils import get_view_for_user


TEST_DOI = "10.1002/mrm.25227"


@pytest.mark.django_db
def test_publication_creation(client):
    user1 = UserFactory()
    user2 = get_anonymous_user()
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    assert g_reg not in user2.groups.all()
    assert Publication.objects.count() == 0

    # only registered users can create a publication
    response = get_view_for_user(
        viewname="publications:create",
        client=client,
        method=client.post,
        data={"identifier": TEST_DOI},
        user=user2,
    )
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
    assert Publication.objects.count() == 0

    response = get_view_for_user(
        viewname="publications:create",
        client=client,
        method=client.post,
        data={"identifier": TEST_DOI},
        user=user1,
    )
    assert response.status_code == 302
    assert Publication.objects.count() == 1
