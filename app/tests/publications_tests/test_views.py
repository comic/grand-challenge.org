import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.utils import get_anonymous_user

from grandchallenge.publications.models import Publication
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.publications_tests.test_models import TEST_CSL
from tests.utils import get_view_for_user


TEST_DOI = "10.1002/mrm.25227"


@pytest.mark.django_db
def test_publication_creation(client, mocker):
    user1 = UserFactory()
    user2 = get_anonymous_user()
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)

    assert g_reg not in user2.groups.all()
    assert Publication.objects.count() == 0

    mocker.patch(
        "grandchallenge.publications.utils.get_doi_csl", return_value=TEST_CSL
    )

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


@pytest.mark.django_db
def test_publication_object_visibilty(client, mocker):
    user1 = UserFactory()
    user2 = UserFactory()

    alg = AlgorithmFactory()
    alg.add_user(user1)
    assert user1.has_perm("view_algorithm", alg)
    assert not user2.has_perm("view_algorithm", alg)

    mocker.patch(
        "grandchallenge.publications.utils.get_doi_csl", return_value=TEST_CSL
    )

    # create publication
    _ = get_view_for_user(
        viewname="publications:create",
        client=client,
        method=client.post,
        data={"identifier": TEST_DOI},
        user=user1,
    )
    # add publication to algorithm
    alg.publications.add(Publication.objects.get())
    alg.save()

    response = get_view_for_user(
        viewname="publications:list",
        client=client,
        method=client.get,
        user=user1,
    )

    assert response.status_code == 200
    assert alg.title in response.rendered_content

    response = get_view_for_user(
        viewname="publications:list",
        client=client,
        method=client.get,
        user=user2,
    )

    assert response.status_code == 200
    assert alg.title not in response.rendered_content
