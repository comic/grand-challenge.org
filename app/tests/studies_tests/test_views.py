import pytest

from tests.factories import UserFactory
from tests.studies_tests import StudyFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_study_display(client):
    study = StudyFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="studies:study-display", user=staff_user
    )
    assert str(study.id) in response.rendered_content


def test_study_create(client):


def tesT_study_update(client):



def test_study_delete(client):
