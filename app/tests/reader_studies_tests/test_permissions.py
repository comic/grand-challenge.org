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


class TwoReaderStudies:
    def __init__(self):
        self.creator = get_rs_creator()
        self.rs1, self.rs2 = ReaderStudyFactory(), ReaderStudyFactory()
        self.editor1, self.reader1, self.editor2, self.reader2 = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        self.rs1.add_editor(user=self.editor1)
        self.rs2.add_editor(user=self.editor2)
        self.rs1.add_reader(user=self.reader1)
        self.rs2.add_reader(user=self.reader2)
        self.u = UserFactory()


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
def test_rs_detail_view_permissions(client):
    rs_set = TwoReaderStudies()

    tests = (
        (None, rs_set.rs1, 302),
        (None, rs_set.rs2, 302),
        (rs_set.creator, rs_set.rs1, 403),
        (rs_set.creator, rs_set.rs2, 403),
        (rs_set.editor1, rs_set.rs1, 200),
        (rs_set.editor1, rs_set.rs2, 403),
        (rs_set.reader1, rs_set.rs1, 200),
        (rs_set.reader1, rs_set.rs2, 403),
        (rs_set.editor2, rs_set.rs1, 403),
        (rs_set.editor2, rs_set.rs2, 200),
        (rs_set.reader2, rs_set.rs1, 403),
        (rs_set.reader2, rs_set.rs2, 200),
        (rs_set.u, rs_set.rs1, 403),
        (rs_set.u, rs_set.rs2, 403),
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
def test_rs_edit_view_permissions(client, view_name):
    rs_set = TwoReaderStudies()

    tests = (
        (None, rs_set.rs1, 302),
        (None, rs_set.rs2, 302),
        (rs_set.creator, rs_set.rs1, 403),
        (rs_set.creator, rs_set.rs2, 403),
        (rs_set.editor1, rs_set.rs1, 200),
        (rs_set.editor1, rs_set.rs2, 403),
        (rs_set.reader1, rs_set.rs1, 403),
        (rs_set.reader1, rs_set.rs2, 403),
        (rs_set.editor2, rs_set.rs1, 403),
        (rs_set.editor2, rs_set.rs2, 200),
        (rs_set.reader2, rs_set.rs1, 403),
        (rs_set.reader2, rs_set.rs2, 403),
        (rs_set.u, rs_set.rs1, 403),
        (rs_set.u, rs_set.rs2, 403),
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
def test_user_autocomplete_permissions(client):
    rs_set = TwoReaderStudies()

    tests = (
        (None, 302),
        (rs_set.creator, 403),
        (rs_set.editor1, 200),
        (rs_set.reader1, 403),
        (rs_set.editor2, 200),
        (rs_set.reader2, 403),
        (rs_set.u, 403),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="reader-studies:users-autocomplete",
            client=client,
            user=test[0],
        )
        assert response.status_code == test[1]
