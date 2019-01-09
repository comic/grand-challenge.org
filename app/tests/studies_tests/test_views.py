import pytest

from tests.factories import StudyFactory, UserFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_study_list(client):
    inserted = StudyFactory()

    staff_user = UserFactory(is_staff=True)
    response = get_view_for_user(
        client=client, viewname="studies:study-list", user=staff_user
    )
    assert str(inserted.id) in response.rendered_content
