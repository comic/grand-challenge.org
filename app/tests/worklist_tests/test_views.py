import pytest

from tests.factories import WorklistFactory, WorklistSetFactory, UserFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_worklist_list(client):
    inserted = WorklistFactory()

    staff_user = UserFactory(is_staff=True)
    response = get_view_for_user(client=client, viewname="worklists:worklist-list", user=staff_user)
    assert str(inserted.id) in response.rendered_content


@pytest.mark.django_db
def test_worklist_set_list(client):
    inserted = WorklistSetFactory()

    staff_user = UserFactory(is_staff=True)
    response = get_view_for_user(client=client, viewname="worklists:set-list", user=staff_user)
    assert str(inserted.id) in response.rendered_content
