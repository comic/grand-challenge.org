import pytest

from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_editor_update_form(client):
    rs, _ = ReaderStudyFactory(), ReaderStudyFactory()

    editor = UserFactory()
    rs.editors_group.user_set.add(editor)

    assert rs.editors_group.user_set.count() == 1

    new_editor = UserFactory()
    response = get_view_for_user(
        viewname="reader-studies:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "ADD"},
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    rs.refresh_from_db()
    assert rs.editors_group.user_set.count() == 2


@pytest.mark.django_db
def test_editor_update_form(client):
    rs, _ = ReaderStudyFactory(), ReaderStudyFactory()

    editor = UserFactory()
    rs.editors_group.user_set.add(editor)

    assert rs.readers_group.user_set.count() == 0

    new_reader = UserFactory()
    response = get_view_for_user(
        viewname="reader-studies:readers-update",
        client=client,
        method=client.post,
        data={"user": new_reader.pk, "action": "ADD"},
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    rs.refresh_from_db()
    assert rs.readers_group.user_set.count() == 1
