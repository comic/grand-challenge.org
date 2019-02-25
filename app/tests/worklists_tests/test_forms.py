import pytest

from tests.factories import UserFactory
from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import get_view_for_user

from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_worklist_list(client):
    list = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:worklist-display", user=staff_user
    )
    assert str(list.id) in response.rendered_content


@pytest.mark.django_db
def test_worklist_create(client):
    form = WorklistCreateForm(data={"name": "test"})
    assert form.is_valid()

    form = WorklistCreateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_worklist_update(client):
    form = WorklistUpdateForm(data={"name": "test"})
    assert form.is_valid()

    form = WorklistUpdateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_worklist_delete(client):
    patient = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        viewname="patients:patient-delete",
        user=staff_user,
        args=patient.id,
    )

    assert response.status_code == 302
    assert patient is None


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
    form = WorklistSetCreateForm(data={"name": "test"})
    assert form.is_valid()

    form = WorklistSetCreateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_worklist_set_update(client):
    form = WorklistSetUpdateForm(data={"name": "test"})
    assert form.is_valid()

    form = WorklistSetUpdateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_worklist_set_delete(client):
    patient = WorklistSetFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        viewname="patients:patient-delete",
        user=staff_user,
        args=patient.id,
    )

    assert response.status_code == 302
    assert patient is None
