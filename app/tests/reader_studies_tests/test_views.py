import pytest
from django.conf import settings
from django.contrib.auth.models import Group

from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_rs_list_permissions(client):
    # Users should login
    response = get_view_for_user(viewname="reader-studies:list", client=client)
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)

    creator = UserFactory()
    g = Group.objects.get(name=settings.READER_STUDY_CREATORS_GROUP_NAME)
    g.user_set.add(creator)

    # Creators should be able to see the create button
    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=creator
    )
    assert response.status_code == 200
    assert "Add a new reader study" in response.rendered_content

    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    reader1 = UserFactory()

    # Readers should only be able to see the studies they have access to
    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=reader1
    )
    assert response.status_code == 200
    assert "Add a new reader study" not in response.rendered_content
    assert str(rs1.pk) not in response.rendered_content
    assert str(rs2.pk) not in response.rendered_content

    rs1.add_reader(user=reader1)

    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=reader1
    )
    assert response.status_code == 200
    assert "Add a new reader study" not in response.rendered_content
    assert str(rs1.pk) in response.rendered_content
    assert str(rs2.pk) not in response.rendered_content

    editor2 = UserFactory()
    rs2.add_editor(user=editor2)

    # Editors should only be able to see the studies that they have access to
    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=editor2
    )
    assert response.status_code == 200
    assert "Add a new reader study" not in response.rendered_content
    assert str(rs1.pk) not in response.rendered_content
    assert str(rs2.pk) in response.rendered_content


@pytest.mark.django_db
def test_rs_create_permissions(client):
    # Users should login
    response = get_view_for_user(viewname="reader-studies:list", client=client)
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)

    creator = UserFactory()
    g = Group.objects.get(name=settings.READER_STUDY_CREATORS_GROUP_NAME)
    g.user_set.add(creator)

    # Creators should be able to get the create view
    response = get_view_for_user(
        viewname="reader-studies:create", client=client, user=creator
    )
    assert response.status_code == 200

    # Normal users should have permission denied
    u = UserFactory()
    response = get_view_for_user(
        viewname="reader-studies:create", client=client, user=u
    )
    assert response.status_code == 403
