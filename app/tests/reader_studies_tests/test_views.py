import io

import pytest
from django.forms import JSONField, ModelChoiceField
from guardian.shortcuts import assign_perm
from requests import put

from grandchallenge.cases.widgets import FlexibleImageField, WidgetChoices
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    DisplaySet,
    InteractiveAlgorithmChoices,
    Question,
)
from grandchallenge.subdomains.utils import reverse
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
            answer_type=Question.AnswerType.TEXT,
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
        method=client.post,
        reverse_kwargs={"slug": rs1.slug, "username": r1.username},
        follow=True,
        user=r1,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.post,
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
        method=client.post,
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
        method=client.post,
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
        method=client.post,
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
            "order[0][column]": 2,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert str(ds.pk) in resp["data"][0][1]


@pytest.mark.django_db
def test_display_set_update_permissions(client):
    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds1 = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)
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


@pytest.mark.django_db
def test_display_set_detail_permissions(client):
    rs = ReaderStudyFactory()

    editor = UserFactory()
    rs.add_editor(editor)

    reader = UserFactory()
    rs.add_reader(reader)

    ds = DisplaySetFactory(reader_study=rs)

    def get_view(_user):
        return get_view_for_user(
            viewname="reader-studies:display-set-detail",
            client=client,
            reverse_kwargs={"slug": rs.slug, "pk": ds.pk},
            user=_user,
        )

    for user in editor, reader:
        response = get_view(user)
        assert response.status_code == 200

    # Removing the roles works
    rs.remove_editor(editor)
    rs.remove_reader(reader)

    for user in (
        editor,
        reader,
        UserFactory(),  # Random user cannot view display set
    ):
        response = get_view(user)
        assert response.status_code == 403


@pytest.mark.django_db
def test_display_set_update(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    rs = ReaderStudyFactory()
    ds1, ds2 = DisplaySetFactory.create_batch(2, reader_study=rs)
    rs.add_editor(user)
    # 3 interfaces of different types
    ci_json = ComponentInterfaceFactory(
        kind="JSON",
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "object",
        },
    )
    ci_json_file = ComponentInterfaceFactory(
        kind="JSON", store_in_database=False
    )
    ci_img = ComponentInterfaceFactory(kind="IMG")
    # create CIVs for those interfaces
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im2)
    civ_json = ComponentInterfaceValueFactory(
        interface=ci_json, value={"foo": "bar"}
    )
    civ_img = ComponentInterfaceValueFactory(interface=ci_img, image=im1)
    civ_json_file = ComponentInterfaceValueFactory(interface=ci_json_file)

    # add 3 CIVs to display set
    ds1.values.set([civ_json, civ_json_file, civ_img])

    # create new civs to update old ones
    civ_img_new = ComponentInterfaceValueFactory(interface=ci_img, image=im2)
    civ_json_file_new = ComponentInterfaceValueFactory(interface=ci_json_file)
    ds2.values.set([civ_json_file_new, civ_img_new])

    # test updating of all 3 interface types
    def do_update():
        return get_view_for_user(
            viewname="reader-studies:display-set-update",
            client=client,
            reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
            data={
                ci_json.slug: '{"foo": "new"}',
                ci_img.slug: str(im2.pk),
                f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_SEARCH.name,
                ci_json_file.slug: str(civ_json_file_new.pk),
                f"value_type_{ci_json_file.slug}": "civ",
                "order": 11,
                "title": "foobar",
            },
            user=user,
            method=client.post,
        )

    with django_capture_on_commit_callbacks(execute=True):
        response = do_update()

    assert response.status_code == 302
    assert response.headers["HX-Redirect"] == reverse(
        "reader-studies:display_sets", kwargs={"slug": rs.slug}
    )

    ds1.refresh_from_db()
    assert ds1.values.count() == 3
    assert not ds1.values.filter(pk=civ_img.pk).exists()
    assert ds1.values.filter(pk=civ_img_new.pk).exists()
    assert not ds1.values.filter(pk=civ_json_file.pk).exists()
    assert ds1.values.filter(pk=civ_json_file_new.pk).exists()
    assert ds1.values.get(interface=ci_json).value == {"foo": "new"}

    assert ds1.order == 11
    assert ds1.title == "foobar"

    n_civs_old = ComponentInterfaceValue.objects.count()

    # test saving without any changes
    with django_capture_on_commit_callbacks(execute=True):
        response = do_update()

    assert response.status_code == 302
    assert response.headers["HX-Redirect"] == reverse(
        "reader-studies:display_sets", kwargs={"slug": rs.slug}
    )
    # no new CIVs have been created
    assert n_civs_old == ComponentInterfaceValue.objects.count()

    ds1.refresh_from_db()
    assert ds1.values.count() == 3
    assert ds1.values.filter(pk=civ_img_new.pk).exists()
    assert ds1.values.filter(pk=civ_json_file_new.pk).exists()
    assert ds1.values.get(interface=ci_json).value == {"foo": "new"}

    assert ds1.order == 11
    assert ds1.title == "foobar"

    # test new json file upload
    upload = UserUploadFactory(filename="file.json", creator=user)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"new": "content"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-update",
            client=client,
            reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
            data={
                ci_json.slug: '{"foo": "new"}',
                ci_img.slug: str(im2.pk),
                f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_SEARCH.name,
                ci_json_file.slug: str(upload.pk),
                f"value_type_{ci_json_file.slug}": "uuid",
                "order": 12,
            },
            user=user,
            method=client.post,
        )
    assert response.status_code == 302
    assert response.headers["HX-Redirect"] == reverse(
        "reader-studies:display_sets", kwargs={"slug": rs.slug}
    )

    ds1.refresh_from_db()
    assert ds1.values.count() == 3
    assert ds1.values.filter(interface=ci_json_file).exists()
    assert (
        ds1.values.filter(interface=ci_json_file).get().file.read()
        == b'{"new": "content"}'
    )
    assert ds1.order == 12
    assert ds1.title == ""

    n_civs_old = ComponentInterfaceValue.objects.count()

    # test removing json file and json value interface values
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-update",
            client=client,
            reverse_kwargs={"pk": ds1.pk, "slug": rs.slug},
            data={
                ci_img.slug: str(im2.pk),
                f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_SEARCH.name,
                "order": 12,
                "title": "foobar_foobar",
            },
            user=user,
            method=client.post,
        )
    assert response.status_code == 302
    assert response.headers["HX-Redirect"] == reverse(
        "reader-studies:display_sets", kwargs={"slug": rs.slug}
    )

    ds1.refresh_from_db()
    assert ds1.values.count() == 1
    assert n_civs_old == ComponentInterfaceValue.objects.count()
    assert ds1.values.filter(pk=civ_img_new.pk).exists()
    assert not ds1.values.filter(pk=civ_json_file_new.pk).exists()
    assert not ds1.values.filter(interface=ci_json).exists()

    assert ds1.order == 12
    assert ds1.title == "foobar_foobar"


@pytest.mark.django_db
def test_add_display_set_to_reader_study(
    client, settings, django_capture_on_commit_callbacks
):
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
    image = ImageFactory()
    assign_perm("cases.view_image", u1, image)
    civ_new_img = ComponentInterfaceValueFactory(
        image=image, interface=ci_img_new
    )
    upload = UserUploadFactory(filename="file.json", creator=u1)
    presigned_urls = upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'{"foo": "bar"}')
    upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    upload.save()

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-create",
            client=client,
            reverse_kwargs={"slug": rs.slug},
            data={
                ci_str.slug: "new-title",
                ci_img.slug: str(im_upload.pk),
                "order": 11,
                f"WidgetChoice-{ci_img.slug}": WidgetChoices.IMAGE_UPLOAD.name,
                ci_img_new.slug: str(image.pk),
                f"WidgetChoice-{ci_img_new.slug}": WidgetChoices.IMAGE_SEARCH.name,
                ci_str_new.slug: "new",
                ci_json.slug: str(upload.pk),
            },
            user=u1,
            method=client.post,
        )

    assert response.status_code == 302
    assert DisplaySet.objects.count() == 2
    ds = DisplaySet.objects.last()
    assert ds.values.count() == 5
    assert ds.values.get(interface=ci_str).value == "new-title"
    assert ds.values.get(interface=ci_img).image.name == "test_grayscale.jpg"
    assert ds.values.get(interface=ci_img_new).image == image
    assert ds.values.get(interface=ci_img_new) == civ_new_img
    assert ds.values.get(interface=ci_str_new).value == "new"
    assert ds.values.get(interface=ci_json).file.read() == b'{"foo": "bar"}'


@pytest.mark.parametrize(
    "interface_kind, store_in_database, field_type",
    (
        ("JSON", False, ModelChoiceField),
        ("JSON", True, JSONField),
        ("IMG", False, FlexibleImageField),
    ),
)
@pytest.mark.django_db
def test_display_set_interfaces_create(
    client, interface_kind, store_in_database, field_type
):
    u1, u2 = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    rs.add_editor(u1)

    ci = ComponentInterfaceFactory(
        kind=interface_kind, store_in_database=store_in_database
    )

    response = get_view_for_user(
        viewname="reader-studies:display-set-interfaces-create",
        client=client,
        reverse_kwargs={"pk": ds.pk, "slug": rs.slug},
        data={"interface": str(ci.pk)},
        user=u1,
    )
    assert not response.context["form"].is_bound
    assert isinstance(
        response.context["form"].fields[str(ci.slug)], field_type
    )


@pytest.mark.django_db
def test_display_set_bulk_delete_permissions(client):
    user, editor = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()
    rs.add_editor(editor)

    ds1, ds2, ds3 = DisplaySetFactory.create_batch(3, reader_study=rs)
    DisplaySetFactory()
    AnswerFactory(display_set=ds1)

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:display-sets-bulk-delete",
        reverse_kwargs={"slug": rs.slug},
        user=editor,
    )
    # ds with answer and ds from other reader study are not in queryset
    assert list(
        response.context["form"].fields["civ_sets_to_delete"].queryset
    ) == [ds2, ds3]

    # for the normal user the queryset is empty
    response = get_view_for_user(
        client=client,
        viewname="reader-studies:display-sets-bulk-delete",
        reverse_kwargs={"slug": rs.slug},
        user=user,
    )
    assert (
        list(response.context["form"].fields["civ_sets_to_delete"].queryset)
        == []
    )


@pytest.mark.django_db
def test_display_set_delete_all_button_disabled(client):
    editor = UserFactory()
    rs = ReaderStudyFactory()
    rs.add_editor(editor)

    AnswerFactory(question__reader_study=rs)

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:display_sets",
        reverse_kwargs={"slug": rs.slug},
        user=editor,
    )

    assert response.status_code == 200
    assert (
        "Cannot delete all display sets: first you need to delete all of the answers for this reader study"
        in str(response.rendered_content)
    )


@pytest.mark.django_db
def test_question_interactive_algorithms_view_permissions(client):
    editor, editor_with_permission, reader = UserFactory.create_batch(3)
    rs = ReaderStudyFactory()

    rs.add_editor(editor)
    rs.add_editor(editor_with_permission)
    rs.add_reader(reader)

    assign_perm(
        "reader_studies.add_interactive_algorithm_to_question",
        editor_with_permission,
    )

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:question-interactive-algorithms",
        reverse_kwargs={"slug": rs.slug},
        data={"answer_type": AnswerType.MASK},
        user=editor,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:question-interactive-algorithms",
        reverse_kwargs={"slug": rs.slug},
        data={"answer_type": AnswerType.MASK},
        user=reader,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:question-interactive-algorithms",
        reverse_kwargs={"slug": rs.slug},
        data={"answer_type": AnswerType.MASK},
        user=editor_with_permission,
    )
    assert response.status_code == 200
    assert InteractiveAlgorithmChoices.ULS23_BASELINE.value in str(
        response.content
    )
