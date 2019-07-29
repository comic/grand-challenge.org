import pytest

from grandchallenge.reader_studies.models import ReaderStudy, Question
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.reader_studies_tests.utils import get_rs_creator, TwoReaderStudies
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


@pytest.mark.django_db
def test_reader_study_create(client):
    # The study creator should automatically get added to the editors group
    creator = get_rs_creator()

    response = get_view_for_user(
        viewname="reader-studies:create",
        client=client,
        method=client.post,
        data={"title": "foo bar"},
        follow=True,
        user=creator,
    )
    assert response.status_code == 200

    rs = ReaderStudy.objects.get(title="foo bar")

    assert rs.slug == "foo-bar"
    assert rs.is_editor(user=creator)
    assert not rs.is_reader(user=creator)


@pytest.mark.django_db
def test_question_create(client):
    rs_set = TwoReaderStudies()

    response = get_view_for_user(
        viewname="reader-studies:add-question",
        client=client,
        method=client.post,
        data={"question_text": "What?", "answer_type": "S", "order": 1},
        reverse_kwargs={"slug": rs_set.rs1.slug},
        follow=True,
        user=rs_set.editor1,
    )
    assert response.status_code == 200

    qs = Question.objects.all()

    assert len(qs) == 1
    assert qs[0].reader_study == rs_set.rs1
    assert qs[0].question_text == "What?"
