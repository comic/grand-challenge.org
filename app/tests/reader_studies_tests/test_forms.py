import html

import pytest
from actstream.actions import is_following
from django.contrib.auth.models import Permission

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from tests.factories import ImageFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests import RESOURCE_PATH
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
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
def test_reader_study_create(client, uploaded_image):
    # The study creator should automatically get added to the editors group
    creator = get_rs_creator()
    ws = WorkstationFactory()

    def try_create_rs(allow_case_navigation):
        return get_view_for_user(
            viewname="reader-studies:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": uploaded_image(),
                "workstation": ws.pk,
                "allow_answer_modification": True,
                "allow_case_navigation": allow_case_navigation,
            },
            follow=True,
            user=creator,
        )

    response = try_create_rs(False)
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    response = try_create_rs(False)
    assert "error_1_id_workstation" not in response.rendered_content
    assert (
        "`allow_case_navigation` must be checked if `allow_answer_modification` is"
        in response.rendered_content
    )

    response = try_create_rs(True)
    assert "error_1_id_workstation" not in response.rendered_content
    assert (
        "`allow_case_navigation` must be checked if `allow_answer_modification` is"
        not in response.rendered_content
    )
    assert response.status_code == 200

    rs = ReaderStudy.objects.get(title="foo bar")

    assert rs.slug == "foo-bar"
    assert rs.is_editor(user=creator)
    assert not rs.is_reader(user=creator)
    assert is_following(user=creator, obj=rs)


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
                "options-TOTAL_FORMS": 2,
                "options-INITIAL_FORMS": 1,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
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
        answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
        direction=Question.Direction.HORIZONTAL,
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
    assert question.answer_type == Question.AnswerType.SINGLE_LINE_TEXT
    assert question.direction == Question.Direction.HORIZONTAL
    assert question.order == 100

    get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.post,
        data={
            "question_text": "bar",
            "answer_type": Question.AnswerType.BOOL,
            "direction": Question.Direction.VERTICAL,
            "order": 200,
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
        },
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=editor,
    )

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.AnswerType.BOOL
    assert question.direction == Question.Direction.VERTICAL
    assert question.order == 200

    AnswerFactory(question=question, answer="true")

    # An answer is added, so changing the question text should no longer be possible
    get_view_for_user(
        viewname="reader-studies:question-update",
        client=client,
        method=client.post,
        data={
            "question_text": "foo",
            "answer_type": Question.AnswerType.SINGLE_LINE_TEXT,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
        },
        reverse_kwargs={"slug": rs.slug, "pk": question.pk},
        follow=True,
        user=editor,
    )

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.AnswerType.BOOL
    assert question.direction == Question.Direction.HORIZONTAL
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
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
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
def test_reader_study_copy(client):
    rs = ReaderStudyFactory(title="copied")
    editor = UserFactory()
    editor2 = UserFactory()
    reader = UserFactory()
    rs.add_reader(reader)
    rs.add_editor(editor)
    rs.add_editor(editor2)
    QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOOL,
        question_text="q1",
    ),
    QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOOL,
        question_text="q2",
    )

    im1, im2 = ImageFactory(), ImageFactory()

    rs.images.set([im1, im2])
    rs.generate_hanging_list()
    rs.case_text = {im1.name: "test", im2.name: "test2"}
    rs.save()

    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "1"},
        user=reader,
        follow=True,
    )

    assert response.status_code == 403
    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "1"},
        user=editor,
        follow=True,
    )

    assert response.status_code == 403
    assert ReaderStudy.objects.count() == 1

    add_perm = Permission.objects.get(
        codename=f"add_{ReaderStudy._meta.model_name}"
    )
    editor.user_permissions.add(add_perm)

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "1"},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 2

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "1"
    assert _rs.images.count() == 0
    assert _rs.questions.count() == 0
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1
    assert _rs.hanging_list == []
    assert _rs.case_text == {}

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "2", "copy_questions": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 3

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "2"
    assert _rs.questions.count() == 2
    assert _rs.images.count() == 0
    assert _rs.hanging_list == []
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "3", "copy_images": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 4

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "3"
    assert _rs.questions.count() == 0
    assert _rs.images.count() == 2
    assert _rs.hanging_list == []
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "4", "copy_hanging_list": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert (
        "Hanging list and case text can only be copied if the images are copied as well"
        in response.rendered_content
    )
    assert ReaderStudy.objects.count() == 4

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "4", "copy_images": True, "copy_hanging_list": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 5

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "4"
    assert _rs.questions.count() == 0
    assert _rs.images.count() == 2
    assert _rs.hanging_list == rs.hanging_list
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "5", "copy_images": True, "copy_case_text": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 6

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "5"
    assert _rs.questions.count() == 0
    assert _rs.images.count() == 2
    assert _rs.hanging_list == []
    assert _rs.case_text == rs.case_text
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "6", "copy_readers": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 7

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "6"
    assert _rs.questions.count() == 0
    assert _rs.images.count() == 0
    assert _rs.hanging_list == []
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 1
    assert _rs.editors_group.user_set.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "7", "copy_editors": True},
        user=editor,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 8

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "7"
    assert _rs.questions.count() == 0
    assert _rs.images.count() == 0
    assert _rs.hanging_list == []
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 2


@pytest.mark.django_db
def test_reader_study_delete(client):
    rs = ReaderStudyFactory()
    editor = UserFactory()
    reader = UserFactory()
    rs.add_editor(editor)
    rs.add_reader(reader)

    assert ReaderStudy.objects.count() == 1
    assert is_following(user=editor, obj=rs)

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
    assert not is_following(user=editor, obj=rs)


@pytest.mark.django_db
def test_reader_study_add_ground_truth(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    q = QuestionFactory(
        reader_study=rs,
        question_text="bar",
        answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
    )
    q0 = QuestionFactory(
        reader_study=rs,
        question_text="bool",
        answer_type=Question.AnswerType.BOOL,
    )
    q1 = QuestionFactory(
        reader_study=rs,
        question_text="choice",
        answer_type=Question.AnswerType.CHOICE,
    )
    q2 = QuestionFactory(
        reader_study=rs,
        question_text="mchoice",
        answer_type=Question.AnswerType.MULTIPLE_CHOICE,
    )
    options = {}
    for i, q_ in enumerate([q1, q2]):
        for x in range(3):
            options[f"{i}-{x}"] = CategoricalOptionFactory(
                question=q_, title=f"option{x}"
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
        f"Fields provided do not match with reader study. Fields should "
        f"be: {','.join(rs.ground_truth_file_headers)}"
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

    with open(RESOURCE_PATH / "ground_truth_wrong_images.csv") as gt:
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
    assert (
        "The following images appear in the file, but not in the hanging "
        "list: im5." in response.rendered_content
    )
    assert (
        "These images appear in the hanging list, but not in the file: im4."
        in response.rendered_content.replace(r"[\n']", "")
    )

    rs.hanging_list = [
        {"primary": "im1"},
        {"primary": "im2"},
        {"primary": "im3", "secondary": "im4"},
    ]
    rs.save()
    assert rs.hanging_list_valid

    with open(RESOURCE_PATH / "ground_truth_invalid.csv") as gt:
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
        html.escape("Option 'option3' is not valid for question choice")
        in response.rendered_content
    )

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

    answer_count = len(rs.hanging_list) * rs.answerable_question_count
    assert Answer.objects.all().count() == answer_count
    assert Answer.objects.filter(is_ground_truth=True).count() == answer_count
    assert Answer.objects.get(images__in=[im1.pk], question=q).answer == "yes"
    assert (
        Answer.objects.get(images__in=[im1.pk], question=q).explanation
        == "explanation, with a comma"
    )
    assert (
        Answer.objects.get(images__in=[im2.pk], question=q).explanation == ""
    )
    assert Answer.objects.get(images__in=[im1.pk], question=q0).answer is True
    assert (
        Answer.objects.get(images__in=[im1.pk], question=q1).answer
        == options["0-1"].pk
    )
    assert sorted(
        Answer.objects.get(images__in=[im1.pk], question=q2).answer
    ) == sorted([options["1-1"].pk, options["1-2"].pk])

    with open(RESOURCE_PATH / "ground_truth_new.csv") as gt:
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
    assert Answer.objects.all().count() == answer_count
    assert Answer.objects.filter(is_ground_truth=True).count() == answer_count
    assert Answer.objects.get(images__in=[im1.pk], question=q).answer == "no"
    assert (
        Answer.objects.get(images__in=[im1.pk], question=q).explanation
        == "new explanation"
    )
    assert (
        Answer.objects.get(images__in=[im2.pk], question=q).explanation
        == "explanation"
    )
    assert Answer.objects.get(images__in=[im1.pk], question=q0).answer is False
    assert (
        Answer.objects.get(images__in=[im1.pk], question=q1).answer
        == options["0-2"].pk
    )
    assert Answer.objects.get(images__in=[im1.pk], question=q2).answer == [
        options["1-0"].pk
    ]
