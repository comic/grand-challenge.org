import pytest

from tests.factories import UserFactory
from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import get_view_for_user

from grandchallenge.subdomains.utils import reverse
from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

"""" Tests the forms available for Worklist CRUD """


@pytest.mark.django_db
def test_worklist_list(client):
    list = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:list-display", user=staff_user
    )
    assert str(list.id) in response.rendered_content


@pytest.mark.django_db
def test_worklist_create(client):
    staff_user = UserFactory(is_staff=True)
    set = WorklistSetFactory()
    data = {"title": "test", "set": set.pk}

    form = WorklistCreateForm(data=data)
    assert form.is_valid()

    form = WorklistCreateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="worklists:list-create",
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
    data = {"title": "test", "set": worklist.set.pk}

    form = WorklistUpdateForm(data=data)
    assert form.is_valid()

    form = WorklistUpdateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("worklists:list-update", kwargs={"pk": worklist.pk}),
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_delete(client):
    worklist = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=staff_user,
        url=reverse("worklists:list-remove", kwargs={"pk": worklist.pk}),
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_set_list(client):
    set = WorklistSetFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:set-display", user=staff_user
    )
    assert str(set.id) in response.rendered_content


@pytest.mark.django_db
def test_worklist_set_create(client):
    staff_user = UserFactory(is_staff=True)
    data = {"title": "test", "user": staff_user.pk}
    form = WorklistSetCreateForm(data=data)
    assert form.is_valid()

    form = WorklistSetCreateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="worklists:set-create",
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_set_update(client):
    staff_user = UserFactory(is_staff=True)
    set = WorklistSetFactory()
    data = {"title": "test", "user": staff_user.pk}
    form = WorklistSetUpdateForm(data=data)
    assert form.is_valid()

    form = WorklistSetUpdateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("worklists:set-update", kwargs={"pk": set.pk}),
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_worklist_set_delete(client):
    set = WorklistSetFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=staff_user,
        url=reverse("worklists:set-remove", kwargs={"pk": set.pk}),
    )

    assert response.status_code == 302
