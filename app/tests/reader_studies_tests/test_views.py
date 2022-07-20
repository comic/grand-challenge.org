import io

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from requests import put

from grandchallenge.reader_studies.models import Answer, DisplaySet, Question
from tests.cases_tests import RESOURCE_PATH
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
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
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
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-detail",
        client=client,
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
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
        viewname="reader-studies:display-set-update",
        client=client,
        reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-update",
        client=client,
        reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
        user=u1,
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname="reader-studies:display-set-update",
        client=client,
        reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
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
    civ_str.refresh_from_db()
    assert civ_str.value == "new-title"

    # A new ds should have been created for civ_img
    assert DisplaySet.objects.count() == 3


@pytest.mark.django_db
def test_add_display_set_to_reader_study(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds1 = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)
    ci_str = ComponentInterfaceFactory(kind="STR")
    ci_img = ComponentInterfaceFactory(kind="IMG")

    ci_img_new = ComponentInterfaceFactory(kind="IMG")
    ci_str_new = ComponentInterfaceFactory(kind="STR")
    ci_json = ComponentInterfaceFactory(kind="JSON", store_in_database=False)

    im1, im2 = ImageFactory.create_batch(2)
    civ_str = ComponentInterfaceValueFactory(
        interface=ci_str, value="civ-title"
    )
    civ_img = ComponentInterfaceValueFactory(interface=ci_img, image=im1)
    ds1.values.set([civ_str, civ_img])

    assert DisplaySet.objects.count() == 1
    response = get_view_for_user(
        viewname="reader-studies:display-set-create",
        client=client,
        reverse_kwargs={"slug": rs.slug},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-create",
        client=client,
        reverse_kwargs={"slug": rs.slug},
        user=u1,
    )

    assert response.status_code == 200

    im_upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "test_grayscale.jpg",
        creator=u1,
    )
    im_upload_new = create_upload_from_file(
        file_path=RESOURCE_PATH / "test_grayscale.png",
        creator=u1,
    )
    upload = UserUploadFactory(filename="file.json", creator=u1)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-create",
            client=client,
            reverse_kwargs={"slug": rs.slug},
            content_type="application/json",
            data={
                ci_str.slug: "new-title",
                ci_img.slug: str(im_upload.pk),
                "order": 11,
                "new_interfaces": [
                    {
                        "interface": ci_img_new.pk,
                        "value": str(im_upload_new.pk),
                    },
                    {"interface": ci_str_new.pk, "value": "new"},
                    {"interface": ci_json.pk, "value": str(upload.pk)},
                ],
            },
            user=u1,
            method=client.post,
        )

    assert response.status_code == 200
    assert DisplaySet.objects.count() == 2
    ds = DisplaySet.objects.last()
    # assert ds.values.count() == 5
    assert ds.values.get(interface=ci_str).value == "new-title"
    assert ds.values.get(interface=ci_img).image.name == "test_grayscale.jpg"
    assert (
        ds.values.get(interface=ci_img_new).image.name == "test_grayscale.png"
    )
    assert ds.values.get(interface=ci_str_new).value == "new"
    assert ds.values.get(interface=ci_json).file.read() == b'{"foo": "bar"}'


@pytest.mark.django_db
def test_add_files_to_display_set(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)
    ci_json = ComponentInterfaceFactory(kind="JSON", store_in_database=False)
    ci_img = ComponentInterfaceFactory(kind="IMG")
    im_upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "test_grayscale.jpg",
        creator=u1,
    )
    civ_json = ComponentInterfaceValueFactory(
        interface=ci_json,
    )
    ds.values.add(civ_json)
    upload = UserUploadFactory(filename="file.json", creator=u1)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    response = get_view_for_user(
        viewname="reader-studies:display-set-files-update",
        client=client,
        reverse_kwargs={
            "pk": ds.pk,
            "interface_pk": ci_json.pk,
            "slug": rs.slug,
        },
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-files-update",
        client=client,
        reverse_kwargs={
            "pk": ds.pk,
            "interface_pk": ci_json.pk,
            "slug": rs.slug,
        },
        user=u1,
    )

    assert response.status_code == 200

    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-files-update",
            client=client,
            reverse_kwargs={
                "pk": ds.pk,
                "interface_pk": ci_json.pk,
                "slug": rs.slug,
            },
            data={"user_upload": str(upload.pk)},
            user=u1,
            method=client.post,
        )

    assert response.status_code == 302
    civ_json.refresh_from_db()
    assert civ_json.file.read() == b'{"foo": "bar"}'

    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-files-update",
            client=client,
            reverse_kwargs={
                "pk": ds.pk,
                "interface_pk": ci_img.pk,
                "slug": rs.slug,
            },
            data={"user_uploads": str(im_upload.pk)},
            user=u1,
            method=client.post,
        )

    assert response.status_code == 302
    civ_img = ds.values.get(interface=ci_img)
    assert civ_img.image.name == "test_grayscale.jpg"


@pytest.mark.django_db
def test_display_set_interfaces_create(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)

    ci_file = ComponentInterfaceFactory(kind="JSON", store_in_database=False)
    ci_value = ComponentInterfaceFactory(kind="JSON", store_in_database=True)
    ci_image = ComponentInterfaceFactory(kind="IMG", store_in_database=False)

    response = get_view_for_user(
        viewname="reader-studies:display-set-interfaces-create",
        client=client,
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
        user=u2,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:display-set-interfaces-create",
        client=client,
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
        user=u1,
    )

    assert response.status_code == 200

    assert not ds.values.filter(interface=ci_value).exists()
    response = get_view_for_user(
        viewname="reader-studies:display-set-interfaces-create",
        client=client,
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
        data={"interface": str(ci_value.pk), "value": '{"foo": "bar"}'},
        user=u1,
        method=client.post,
    )

    assert response.status_code == 302
    civ = ds.values.get(interface=ci_value)
    assert civ.value == {"foo": "bar"}

    assert not ds.values.filter(interface=ci_file).exists()
    upload = UserUploadFactory(filename="file.json", creator=u1)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-interfaces-create",
            client=client,
            reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
            data={"interface": str(ci_file.pk), "value": str(upload.pk)},
            user=u1,
            method=client.post,
        )

    assert response.status_code == 302
    civ = ds.values.get(interface=ci_file)
    assert civ.file.read() == b'{"foo": "bar"}'

    assert not ds.values.filter(interface=ci_image).exists()
    upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "test_grayscale.jpg",
        creator=u1,
    )
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-interfaces-create",
            client=client,
            reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
            data={"interface": str(ci_image.pk), "value": str(upload.pk)},
            user=u1,
            method=client.post,
        )

    assert response.status_code == 302
    civ = ds.values.get(interface=ci_image)
    assert civ.image.name == "test_grayscale.jpg"
