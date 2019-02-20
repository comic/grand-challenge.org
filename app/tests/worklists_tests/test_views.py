import pytest

from tests.factories import UserFactory
from tests.worklists_tests import WorklistFactory, WorklistSetFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_worklist_list(client):
    list = WorklistFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:worklist-display", user=staff_user
    )
    assert str(list.id) in response.rendered_content


def test_study_create(client):


def tesT_study_update(client):


def test_study_delete(client):


@pytest.mark.django_db
def test_worklist_set_list(client):
    set = WorklistSetFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="worklists:set-display", user=staff_user
    )
    assert str(set.id) in response.rendered_content


def test_study_create(client):


def tesT_study_update(client):


def test_study_delete(client):
