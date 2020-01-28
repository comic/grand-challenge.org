import pytest

from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from tests.factories import ImageFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests import RESOURCE_PATH
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies, get_rs_creator
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_editor_update_form(client):
    rs, _ = ReaderStudyFactory(), ReaderStudyFactory()

    editor = UserFactory()
    rs.editors_group.user_set.add(editor)

    assert rs.editors_group.user_set.count() == 1

    new_editor = UserFactory()
    assert not rs.is_editor(user=new_editor)
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
    assert rs.is_editor(user=new_editor)

    response = get_view_for_user(
        viewname="reader-studies:editors-update",
        client=client,
        method=client.post,
        data={"user": new_editor.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    rs.refresh_from_db()
    assert rs.editors_group.user_set.count() == 1
    assert not rs.is_editor(user=new_editor)


@pytest.mark.django_db
def test_reader_update_form(client):
    rs, _ = ReaderStudyFactory(), ReaderStudyFactory()

    editor = UserFactory()
    rs.editors_group.user_set.add(editor)

    assert rs.readers_group.user_set.count() == 0

    new_reader = UserFactory()
    assert not rs.is_reader(user=new_reader)
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
    assert rs.is_reader(user=new_reader)

    response = get_view_for_user(
        viewname="reader-studies:readers-update",
        client=client,
        method=client.post,
        data={"user": new_reader.pk, "action": "REMOVE"},
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200

    rs.refresh_from_db()
    assert rs.readers_group.user_set.count() == 0
    assert not rs.is_reader(user=new_reader)


@pytest.mark.django_db
def test_reader_study_create(client):
    # The study creator should automatically get added to the editors group
    creator = get_rs_creator()
    ws = WorkstationFactory()

    def try_create_rs():
        return get_view_for_user(
            viewname="reader-studies:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": get_temporary_image(),
                "workstation": ws.pk,
            },
            follow=True,
            user=creator,
        )

    response = try_create_rs()
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    response = try_create_rs()
    assert "error_1_id_workstation" not in response.rendered_content
    assert response.status_code == 200

    rs = ReaderStudy.objects.get(title="foo bar")

    assert rs.slug == "foo-bar"
    assert rs.is_editor(user=creator)
    assert not rs.is_reader(user=creator)


@pytest.mark.django_db
def test_question_create(client):
    rs_set = TwoReaderStudies()

    tests = (
        (None, 0, 302),
        (rs_set.editor1, 1, 302),
        (rs_set.reader1, 0, 403),
        (rs_set.editor2, 0, 403),
        (rs_set.reader2, 0, 403),
        (rs_set.u, 0, 403),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="reader-studies:add-question",
            client=client,
            method=client.post,
            data={
                "question_text": "What?",
                "answer_type": "STXT",
                "order": 1,
                "image_port": "",
                "direction": "H",
            },
            reverse_kwargs={"slug": rs_set.rs1.slug},
            user=test[0],
        )
        assert response.status_code == test[2]

        qs = Question.objects.all()

        assert len(qs) == test[1]
        if test[1] > 0:
            question = qs[0]
            assert question.reader_study == rs_set.rs1
            assert question.question_text == "What?"
            question.delete()


@pytest.mark.django_db
def test_question_update(client):
    rs = ReaderStudyFactory()
    editor = UserFactory()
    reader = UserFactory()
    rs.editors_group.user_set.add(editor)
    rs.readers_group.user_set.add(reader)

    question = QuestionFactory(
        question_text="foo",
        reader_study=rs,
        answer_type=Question.ANSWER_TYPE_SINGLE_LINE_TEXT,
        direction=Question.DIRECTION_HORIZONTAL,
        order=100,
    )

    response = get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=reader,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200

    assert question.question_text == "foo"
    assert question.answer_type == Question.ANSWER_TYPE_SINGLE_LINE_TEXT
    assert question.direction == Question.DIRECTION_HORIZONTAL
    assert question.order == 100

    get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.post,
        data={
            "question_text": "bar",
            "answer_type": Question.ANSWER_TYPE_BOOL,
            "direction": Question.DIRECTION_VERTICAL,
            "order": 200,
        },
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=editor,
    )

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.ANSWER_TYPE_BOOL
    assert question.direction == Question.DIRECTION_VERTICAL
    assert question.order == 200

    AnswerFactory(question=question, answer="true")

    # An answer is added, so changing the question text should no longer be possible
    get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.post,
        data={
            "question_text": "foo",
            "answer_type": Question.ANSWER_TYPE_SINGLE_LINE_TEXT,
            "direction": Question.DIRECTION_HORIZONTAL,
            "order": 100,
        },
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=editor,
    )

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.ANSWER_TYPE_BOOL
    assert question.direction == Question.DIRECTION_HORIZONTAL
    assert question.order == 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,port,questions_created",
    (
        ("STXT", "", 1),
        ("STXT", "M", 0),
        ("STXT", "S", 0),
        ("HEAD", "", 1),
        ("HEAD", "M", 0),
        ("HEAD", "S", 0),
        ("BOOL", "", 1),
        ("BOOL", "M", 0),
        ("BOOL", "S", 0),
        ("2DBB", "", 0),
        ("2DBB", "M", 1),
        ("2DBB", "S", 1),
    ),
)
def test_image_port_only_with_bounding_box(
    client, answer_type, port, questions_created
):
    # The image_port should only be set when using a bounding box
    rs_set = TwoReaderStudies()

    assert Question.objects.all().count() == 0

    response = get_view_for_user(
        viewname="reader-studies:add-question",
        client=client,
        method=client.post,
        data={
            "question_text": "What?",
            "answer_type": answer_type,
            "order": 1,
            "image_port": port,
            "direction": "H",
        },
        reverse_kwargs={"slug": rs_set.rs1.slug},
        user=rs_set.editor1,
    )

    if questions_created == 1:
        assert response.status_code == 302
    else:
        assert response.status_code == 200

    assert Question.objects.all().count() == questions_created


@pytest.mark.django_db
def test_reader_study_delete(client):
    rs = ReaderStudyFactory()
    editor = UserFactory()
    reader = UserFactory()
    rs.editors_group.user_set.add(editor)
    rs.readers_group.user_set.add(reader)

    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:delete",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=reader,
    )

    assert response.status_code == 403
    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:delete",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert "Confirm Deletion" in response.rendered_content

    response = get_view_for_user(
        viewname="reader-studies:delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 0


@pytest.mark.django_db
def test_reader_study_add_ground_truth(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    q = QuestionFactory(
        reader_study=rs,
        question_text="bar",
        answer_type=Question.ANSWER_TYPE_SINGLE_LINE_TEXT,
    )
    QuestionFactory(
        reader_study=rs,
        question_text="bool",
        answer_type=Question.ANSWER_TYPE_BOOL,
    )
    im1, im2, im3, im4 = (
        ImageFactory(name="im1"),
        ImageFactory(name="im2"),
        ImageFactory(name="im3"),
        ImageFactory(name="im4"),
    )
    rs.images.set([im1.pk, im2.pk, im3.pk, im4.pk])
    rs.hanging_list = [
        {"primary": "im1"},
        {"primary": "im2"},
        {"primary": "im3"},
        {"secondary": "im4"},
    ]
    rs.save()
    assert rs.hanging_list_valid

    editor = UserFactory()
    reader = UserFactory()
    rs.editors_group.user_set.add(editor)
    rs.readers_group.user_set.add(reader)

    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=reader,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert Answer.objects.all().count() == 0

    with open(RESOURCE_PATH / "ground_truth.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200
    assert (
        "Fields provided do not match with reader study"
        in response.rendered_content
    )

    q.question_text = "foo"
    q.save()

    with open(RESOURCE_PATH / "ground_truth.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200
    assert (
        "Images provided do not match hanging protocol"
        in response.rendered_content
    )

    rs.hanging_list = [
        {"primary": "im1"},
        {"primary": "im2"},
        {"primary": "im3", "secondary": "im4"},
    ]
    rs.save()
    assert rs.hanging_list_valid

    with open(RESOURCE_PATH / "ground_truth_wrong_boolean.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200
    assert "Expected 1 or 0 for answer type BOOL." in response.rendered_content

    with open(RESOURCE_PATH / "ground_truth.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200
    assert Answer.objects.all().count() == 6
    assert Answer.objects.filter(is_ground_truth=True).count() == 6

    with open(RESOURCE_PATH / "ground_truth.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200
    assert (
        "Ground truth already added for this question/image combination"
        in response.rendered_content
    )
    assert Answer.objects.all().count() == 6
    assert Answer.objects.filter(is_ground_truth=True).count() == 6
