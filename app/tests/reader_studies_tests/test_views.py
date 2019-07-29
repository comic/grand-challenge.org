import pytest
from django.conf import settings
from django.contrib.auth.models import Group

from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


def get_rs_creator():
    creator = UserFactory()
    g = Group.objects.get(name=settings.READER_STUDY_CREATORS_GROUP_NAME)
    g.user_set.add(creator)
    return creator


@pytest.mark.django_db
def test_rs_list_permissions(client):
    # Users should login
    response = get_view_for_user(viewname="reader-studies:list", client=client)
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)

    creator = get_rs_creator()

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

    creator = get_rs_creator()

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


@pytest.mark.django_db
def test_rs_detail_view(client):
    creator = get_rs_creator()
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    editor1, reader1, editor2, reader2 = (
        UserFactory(),
        UserFactory(),
        UserFactory(),
        UserFactory(),
    )
    rs1.add_editor(user=editor1)
    rs2.add_editor(user=editor2)
    rs1.add_reader(user=reader1)
    rs2.add_reader(user=reader2)
    u = UserFactory()

    tests = (
        (None, rs1, 302),
        (None, rs2, 302),
        (creator, rs1, 403),
        (creator, rs2, 403),
        (editor1, rs1, 200),
        (editor1, rs2, 403),
        (reader1, rs1, 200),
        (reader1, rs2, 403),
        (editor2, rs1, 403),
        (editor2, rs2, 200),
        (reader2, rs1, 403),
        (reader2, rs2, 200),
        (u, rs1, 403),
        (u, rs2, 403),
    )

    for test in tests:
        response = get_view_for_user(
            url=test[1].get_absolute_url(), client=client, user=test[0]
        )
        assert response.status_code == test[2]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view_name",
    [
        "update",
        "add-images",
        "add-question",
        "editors-update",
        "readers-update",
    ],
)
def test_rs_edit_view(client, view_name):
    creator = get_rs_creator()
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    editor1, reader1, editor2, reader2 = (
        UserFactory(),
        UserFactory(),
        UserFactory(),
        UserFactory(),
    )
    rs1.add_editor(user=editor1)
    rs2.add_editor(user=editor2)
    rs1.add_reader(user=reader1)
    rs2.add_reader(user=reader2)
    u = UserFactory()

    tests = (
        (None, rs1, 302),
        (None, rs2, 302),
        (creator, rs1, 403),
        (creator, rs2, 403),
        (editor1, rs1, 200),
        (editor1, rs2, 403),
        (reader1, rs1, 403),
        (reader1, rs2, 403),
        (editor2, rs1, 403),
        (editor2, rs2, 200),
        (reader2, rs1, 403),
        (reader2, rs2, 403),
        (u, rs1, 403),
        (u, rs2, 403),
    )

    for test in tests:
        response = get_view_for_user(
            viewname=f"reader-studies:{view_name}",
            client=client,
            user=test[0],
            reverse_kwargs={"slug": test[1].slug},
        )
        assert response.status_code == test[2]


@pytest.mark.django_db
def test_user_autocomplete(client):
    creator = get_rs_creator()
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    editor1, reader1, editor2, reader2 = (
        UserFactory(),
        UserFactory(),
        UserFactory(),
        UserFactory(),
    )
    rs1.add_editor(user=editor1)
    rs2.add_editor(user=editor2)
    rs1.add_reader(user=reader1)
    rs2.add_reader(user=reader2)
    u = UserFactory()

    tests = (
        (None, 302),
        (creator, 403),
        (editor1, 200),
        (reader1, 403),
        (editor2, 200),
        (reader2, 403),
        (u, 403),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="reader-studies:users-autocomplete",
            client=client,
            user=test[0],
        )
        assert response.status_code == test[1]
