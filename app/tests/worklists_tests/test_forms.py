import pytest

from tests.factories import UserFactory
from tests.worklists_tests.factories import WorklistFactory
from tests.utils import get_view_for_user

from grandchallenge.subdomains.utils import reverse
from grandchallenge.worklists.forms import WorklistForm

"""" Tests the forms available for Worklist CRUD """


@pytest.mark.django_db
def test_worklist_list(client):
    worklist = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:list", user=staff_user
    )
    assert str(worklist.id) in response.rendered_content


@pytest.mark.django_db
def test_worklist_create(client):
    staff_user = UserFactory(is_staff=True)
    data = {"title": "test", "user": staff_user.pk}

    form = WorklistForm(data=data)
    assert form.is_valid()

    form = WorklistForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="worklists:create",
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_update(client):
    staff_user = UserFactory(is_staff=True)
    worklist = WorklistFactory()
    data = {"title": "test", "user": staff_user.pk}

    form = WorklistForm(data=data)
    assert form.is_valid()

    form = WorklistForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("worklists:update", kwargs={"pk": worklist.pk}),
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_delete(client):
    staff_user = UserFactory(is_staff=True)
    worklist = WorklistFactory()

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=staff_user,
        url=reverse("worklists:delete", kwargs={"pk": worklist.pk}),
    )

    assert response.status_code == 302
