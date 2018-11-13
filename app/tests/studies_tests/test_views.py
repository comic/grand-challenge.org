import pytest

from tests.factories import StudyFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_patient_list(client):
    visible = StudyFactory(hidden=False)
    invisible = StudyFactory(hidden=True)

    response = get_view_for_user(client=client, viewname="studies:study-list")

    assert visible.id in response.rendered_content
    assert invisible.id not in response.rendered_content
