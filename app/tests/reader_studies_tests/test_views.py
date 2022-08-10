import io

import pytest

from grandchallenge.reader_studies.models import Answer, DisplaySet, Question
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_example_ground_truth(client, tmpdir):
    rs = ReaderStudyFactory()
    reader, editor = UserFactory(), UserFactory()
    q1, q2, q3 = (
        QuestionFactory(
            reader_study=rs,
            question_text="q1",
            answer_type=Question.AnswerType.BOOL,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q2",
            answer_type=Question.AnswerType.CHOICE,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q3",
            answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
        ),
    )
    CategoricalOptionFactory(question=q2, title="option")
    ds = DisplaySetFactory.create_batch(3, reader_study=rs)
    rs.add_reader(reader)
    rs.add_editor(editor)
    rs.save()

    response = get_view_for_user(
        viewname="reader-studies:example-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=reader,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:example-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200
    assert Answer.objects.count() == 0

    gt = io.BytesIO()
    gt.write(response.content)
    gt.seek(0)
    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        data={"ground_truth": gt},
        user=editor,
    )
    assert response.status_code == 200
    assert (
        Answer.objects.count()
        == rs.display_sets.count() * rs.questions.count()
    )
    for ds in rs.display_sets.all():
        for question in [q1, q2, q3]:
            assert Answer.objects.filter(
                display_set=ds, question=question, is_ground_truth=True
            ).exists()


@pytest.mark.django_db
def test_answer_remove_for_user(client):
    r1, r2, editor = UserFactory(), UserFactory(), UserFactory()
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    for rs in [rs1, rs2]:
        rs.add_reader(r1)
        rs.add_reader(r2)
        rs.add_editor(editor)
        q = QuestionFactory(
            reader_study=rs,
            question_text="q1",
            answer_type=Question.AnswerType.BOOL,
        )
        ds = DisplaySetFactory(reader_study=rs)
        AnswerFactory(creator=r1, question=q, answer=True, display_set=ds)
        AnswerFactory(creator=r2, question=q, answer=True, display_set=ds)

    assert Answer.objects.count() == 4

    response = get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.delete,
        reverse_kwargs={"slug": rs1.slug, "username": r1.username},
        follow=True,
        user=r1,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.delete,
        reverse_kwargs={"slug": rs1.slug, "username": r1.username},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert Answer.objects.count() == 3
    assert (
        Answer.objects.filter(creator=r1, question__reader_study=rs1).count()
        == 0
    )
    assert (
        Answer.objects.filter(creator=r2, question__reader_study=rs1).count()
        == 1
    )
    assert (
        Answer.objects.filter(creator=r1, question__reader_study=rs2).count()
        == 1
    )
    assert (
        Answer.objects.filter(creator=r2, question__reader_study=rs2).count()
        == 1
    )


@pytest.mark.django_db
def test_answer_remove_ground_truth(client):
    reader, editor = UserFactory.create_batch(2)
    rs1, rs2 = ReaderStudyFactory(title="rs1"), ReaderStudyFactory(title="rs2")
    for rs in [rs1, rs2]:
        ds = DisplaySetFactory(reader_study=rs)
        q = QuestionFactory(reader_study=rs)
        rs.add_reader(reader)
        rs.add_editor(editor)
        AnswerFactory(
            question=q,
            display_set=ds,
            is_ground_truth=False,
            answer=f"a-{rs.title}",
        )
        AnswerFactory(
            question=q,
            display_set=ds,
            is_ground_truth=True,
            answer=f"gt-{rs.title}",
        )

    response = get_view_for_user(
        viewname="reader-studies:ground-truth-remove",
        reverse_kwargs={"slug": rs1.slug},
        user=reader,
        client=client,
        method=client.delete,
        content_type="application/json",
    )
    assert response.status_code == 403
    assert Answer.objects.filter(answer=f"a-{rs1.title}").exists()
    assert Answer.objects.filter(answer=f"gt-{rs1.title}").exists()
    assert Answer.objects.filter(answer=f"a-{rs2.title}").exists()
    assert Answer.objects.filter(answer=f"gt-{rs2.title}").exists()

    response = get_view_for_user(
        viewname="reader-studies:ground-truth-remove",
        reverse_kwargs={"slug": rs1.slug},
        user=editor,
        client=client,
        method=client.delete,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert Answer.objects.filter(answer=f"a-{rs1.title}").exists()
    assert not Answer.objects.filter(answer=f"gt-{rs1.title}").exists()
    assert Answer.objects.filter(answer=f"a-{rs2.title}").exists()
    assert Answer.objects.filter(answer=f"gt-{rs2.title}").exists()


@pytest.mark.django_db
def test_question_delete(client):
    rs = ReaderStudyFactory()
    r1, editor = UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_editor(editor)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    assert Question.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        follow=True,
        user=r1,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )

    assert response.status_code == 302
    assert Question.objects.count() == 0
    assert str(rs) in response.url


@pytest.mark.django_db
def test_question_delete_disabled_for_questions_with_answers(client):
    rs = ReaderStudyFactory()
    r1, editor = UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_editor(editor)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    AnswerFactory(creator=r1, question=q, answer=True)

    assert Answer.objects.count() == 1
    assert Question.objects.count() == 1
    assert not q.is_fully_editable

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )

    assert response.status_code == 403
    assert Question.objects.count() == 1

    # if answer is deleted, deletion of the question is possible again
    get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.delete,
        reverse_kwargs={"slug": rs.slug, "username": r1.username},
        follow=True,
        user=editor,
    )

    assert Answer.objects.count() == 0

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )
    assert response.status_code == 302
    assert Question.objects.count() == 0


@pytest.mark.django_db
def test_reader_study_list_view_filter(client):
    user = UserFactory()
    rs1, rs2, pubrs = (
        ReaderStudyFactory(),
        ReaderStudyFactory(),
        ReaderStudyFactory(
            public=True,
        ),
    )
    rs1.add_reader(user)

    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=user
    )

    assert response.status_code == 200
    assert rs1.get_absolute_url() in response.rendered_content
    assert rs2.get_absolute_url() not in response.rendered_content
    assert pubrs.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_reader_study_display_set_list(client):
    user = UserFactory()
    rs = ReaderStudyFactory()
    rs.add_editor(user)

    civ = ComponentInterfaceValueFactory(image=ImageFactory())
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

    response = get_view_for_user(
        viewname="reader-studies:display_sets",
        reverse_kwargs={"slug": rs.slug},
        client=client,
        user=user,
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname="reader-studies:display_sets",
        reverse_kwargs={"slug": rs.slug},
        client=client,
        user=user,
        method=client.get,
        follow=True,
        data={
            "length": 10,
            "draw": 1,
            "order[0][dir]": "desc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert str(ds.pk) in resp["data"][0][0]


@pytest.mark.django_db
def test_display_set_detail(client):
    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)
    civ = ComponentInterfaceValueFactory(value="civ-title")
    ds.values.add(civ)

    response = get_view_for_user(
        viewname="reader-studies:display-set-detail",
        client=client,
        reverse_kwargs={"pk": ds.pk},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-detail",
        client=client,
        reverse_kwargs={"pk": ds.pk},
        user=u1,
    )

    assert response.status_code == 200
    assert "civ-title" in response.rendered_content


@pytest.mark.django_db
def test_display_set_update(client):
    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds1, ds2 = DisplaySetFactory.create_batch(2, reader_study=rs)
    rs.add_editor(u1)
    ci_str = ComponentInterfaceFactory(kind="STR")
    ci_img = ComponentInterfaceFactory(kind="IMG")
    im1, im2 = ImageFactory.create_batch(2)
    civ_str = ComponentInterfaceValueFactory(
        interface=ci_str, value="civ-title"
    )
    civ_img = ComponentInterfaceValueFactory(interface=ci_img, image=im1)
    ds1.values.set([civ_str, civ_img])

    civ_img_new = ComponentInterfaceValueFactory(interface=ci_img, image=im2)
    ds2.values.add(civ_img_new)

    assert DisplaySet.objects.count() == 2
    response = get_view_for_user(
        viewname="reader-studies:display-set-detail",
        client=client,
        reverse_kwargs={"pk": ds1.pk},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-update",
        client=client,
        reverse_kwargs={"pk": ds1.pk},
        data={
            ci_str.slug: "new-title",
            ci_img.slug: str(civ_img_new.pk),
            "order": 11,
        },
        user=u1,
        method=client.post,
    )

    assert response.status_code == 302
    assert not ds1.values.filter(pk=civ_img.pk).exists()
    assert ds1.values.filter(pk=civ_img_new.pk).exists()
    assert not ds1.values.filter(pk=civ_str.pk).exists()
    assert ds1.values.filter(interface__kind="STR").get().value == "new-title"

    # Two new ds should have been created, one for civ_img and one for civ_str
    assert DisplaySet.objects.count() == 4


@pytest.mark.django_db
def test_pdf_report_permissions(client):
    editor, reader = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    rs.add_editor(editor)
    rs.add_reader(reader)
    display_set = DisplaySetFactory(reader_study=rs)

    response = get_view_for_user(
        viewname="reader-studies:display-set-pdf-report",
        reverse_kwargs={
            "slug": rs.slug,
            "pk": display_set.pk,
            "username": reader.username,
        },
        client=client,
        user=reader,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-pdf-report",
        reverse_kwargs={
            "slug": rs.slug,
            "pk": display_set.pk,
            "username": reader.username,
        },
        client=client,
        user=editor,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_pdf_report_content(client):
    editor, reader = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    rs.add_editor(editor)
    rs.add_reader(reader)
    ds1, ds2 = DisplaySetFactory.create_batch(2, reader_study=rs)

    q1 = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.NUMBER,
        question_text="Number question",
    )
    q2 = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOUNDING_BOX_2D,
        question_text="Bounding box question",
    )
    q3 = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.MASK,
        question_text="Mask question",
    )
    q4 = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.NUMBER,
        question_text="Number question 2",
    )
    number_gt_answer = AnswerFactory(
        question=q1,
        creator=reader,
        answer=1,
        is_ground_truth=True,
        display_set=ds1,
    )
    number_answer_reader = AnswerFactory(
        question=q1,
        creator=reader,
        answer=2,
        is_ground_truth=False,
        display_set=ds1,
    )
    number_answer_editor = AnswerFactory(
        question=q1,
        creator=editor,
        answer=3,
        is_ground_truth=False,
        display_set=ds1,
    )
    number_answer_ds2 = AnswerFactory(
        question=q1,
        creator=reader,
        answer=4,
        is_ground_truth=False,
        display_set=ds2,
    )
    number_empty_answer = AnswerFactory(
        question=q4,
        creator=editor,
        answer=None,
        is_ground_truth=False,
        display_set=ds1,
    )
    annotation_answer = AnswerFactory(
        question=q2,
        creator=reader,
        answer={
            "version": {"major": 1, "minor": 0},
            "type": "2D bounding box",
            "name": "test_name",
            "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
        },
        is_ground_truth=False,
        display_set=ds1,
    )
    img = ImageFactory()
    image_answer = AnswerFactory(
        question=q3,
        creator=reader,
        answer_image=img,
        is_ground_truth=False,
        display_set=ds1,
    )
    response = get_view_for_user(
        viewname="reader-studies:display-set-pdf-report",
        reverse_kwargs={
            "slug": rs.slug,
            "pk": ds1.pk,
            "username": reader.username,
        },
        client=client,
        user=editor,
    )
    assert response.status_code == 200
    assert str(rs) in str(response.context["reader_study"])
    assert str(ds1) in str(response.context["display_set"])
    assert str(ds2) not in str(response.context["display_set"])
    assert str(reader) in str(response.context["user"])
    assert number_answer_reader in response.context["answers"]

    assert number_answer_editor not in response.context["answers"]
    assert number_gt_answer not in response.context["answers"]
    assert number_answer_ds2 not in response.context["answers"]
    assert number_empty_answer not in response.context["answers"]
    assert annotation_answer not in response.context["answers"]
    assert image_answer not in response.context["answers"]
