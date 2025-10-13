import io

import pytest
from django.forms import JSONField
from django.test import override_settings
from guardian.shortcuts import assign_perm
from pytest_django.asserts import assertContains, assertNotContains
from requests import put

from grandchallenge.cases.widgets import FlexibleImageField, ImageWidgetChoices
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    FlexibleFileField,
)
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    DisplaySet,
    Question,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload
from tests.cases_tests import RESOURCE_PATH
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
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
        viewname="reader-studies:example-ground-truth-csv",
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
        viewname="reader-studies:add-ground-truth-csv",
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
def test_ground_truth_delete(client):
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
        viewname="reader-studies:ground-truth-delete",
        reverse_kwargs={"slug": rs1.slug},
        user=reader,
        client=client,
        method=client.post,
    )
    assert response.status_code == 403
    assert Answer.objects.filter(answer=f"a-{rs1.title}").exists()
    assert Answer.objects.filter(answer=f"gt-{rs1.title}").exists()
    assert Answer.objects.filter(answer=f"a-{rs2.title}").exists()
    assert Answer.objects.filter(answer=f"gt-{rs2.title}").exists()

    response = get_view_for_user(
        viewname="reader-studies:ground-truth-delete",
        reverse_kwargs={"slug": rs1.slug},
        user=editor,
        client=client,
        method=client.post,
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
        kind=InterfaceKindChoices.ANY,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "object",
        },
    )
    ci_json_file = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )
    ci_img = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)
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
                **get_interface_form_data(
                    interface_slug=ci_json.slug, data='{"foo": "new"}'
                ),
                **get_interface_form_data(
                    interface_slug=ci_img.slug,
                    data=str(im2.pk),
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=ci_json_file.slug,
                    data=str(civ_json_file_new.pk),
                    existing_data=True,
                ),
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
                **get_interface_form_data(
                    interface_slug=ci_json.slug, data='{"foo": "new"}'
                ),
                **get_interface_form_data(
                    interface_slug=ci_img.slug,
                    data=str(im2.pk),
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=ci_json_file.slug, data=str(upload.pk)
                ),
                "order": 12,
            },
            user=user,
            method=client.post,
        )
    assert not UserUpload.objects.filter(pk=upload.pk).exists()
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
                f"widget-choice-{ci_img.slug}": ImageWidgetChoices.IMAGE_SEARCH.name,
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
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_img = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)

    ci_img_new = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_IMAGE
    )
    ci_str_new = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_json = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )

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
                **get_interface_form_data(
                    interface_slug=ci_str.slug, data="new-title"
                ),
                **get_interface_form_data(
                    interface_slug=ci_img.slug, data=str(im_upload.pk)
                ),
                **get_interface_form_data(
                    interface_slug=ci_img_new.slug,
                    data=str(image.pk),
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=ci_str_new.slug, data="new"
                ),
                **get_interface_form_data(
                    interface_slug=ci_json.slug, data=str(upload.pk)
                ),
                "order": 11,
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


@pytest.mark.django_db
def test_add_display_set_update_when_disabled(client):
    editor = UserFactory()
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    rs.add_editor(editor)
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)

    # add an answer for the ds
    AnswerFactory(question__reader_study=rs, display_set=ds, answer="true")

    response = get_view_for_user(
        viewname="reader-studies:display-set-update",
        client=client,
        reverse_kwargs={"slug": rs.slug, "pk": ds.pk},
        data={
            **get_interface_form_data(
                interface_slug=ci_str.slug, data="new-content"
            ),
        },
        user=editor,
        method=client.post,
    )
    assert response.status_code == 302

    assert Notification.objects.count() == 1
    notification = Notification.objects.first()
    assert notification.user == editor
    assert notification.message == "An unexpected error occurred"


@pytest.mark.parametrize(
    "interface_kind, store_in_database, field_type",
    (
        (InterfaceKindChoices.ANY, False, FlexibleFileField),
        (InterfaceKindChoices.ANY, True, JSONField),
        (InterfaceKindChoices.PANIMG_IMAGE, False, FlexibleImageField),
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
        response.context["form"].fields[
            f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"
        ],
        field_type,
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
    assert {
        *response.context["form"].fields["civ_sets_to_delete"].queryset
    } == {ds2, ds3}

    # for the normal user the queryset is empty
    response = get_view_for_user(
        client=client,
        viewname="reader-studies:display-sets-bulk-delete",
        reverse_kwargs={"slug": rs.slug},
        user=user,
    )
    assert {
        *response.context["form"].fields["civ_sets_to_delete"].queryset
    } == set()


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


@pytest.mark.django_db
def test_display_set_upload_corrupt_image(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    editor = UserFactory()
    rs = ReaderStudyFactory()
    rs.add_editor(editor)
    ci_img = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)

    im_upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "corrupt.png",
        creator=editor,
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:display-set-create",
            client=client,
            reverse_kwargs={"slug": rs.slug},
            data={
                **get_interface_form_data(
                    interface_slug=ci_img.slug, data=str(im_upload.pk)
                ),
                "order": 11,
            },
            user=editor,
            method=client.post,
        )

    assert response.status_code == 302
    assert DisplaySet.objects.count() == 1
    ds = DisplaySet.objects.get()
    assert ds.values.count() == 0
    assert Notification.objects.count() == 1
    notification = Notification.objects.get()
    assert notification.user == editor
    assert "1 file could not be imported" in notification.description


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewname",
    [
        "reader-studies:ground-truth",
        "reader-studies:add-ground-truth-csv",
        "reader-studies:add-ground-truth-answers",
        "reader-studies:add-answers-from-ground-truth",
    ],
)
def test_ground_truth_views(client, viewname):
    rs = ReaderStudyFactory()

    editor, reader, a_user = UserFactory.create_batch(3)
    rs.add_editor(editor)
    rs.add_reader(reader)

    for usr in [reader, a_user]:
        response = get_view_for_user(
            client=client,
            viewname=viewname,
            reverse_kwargs={"slug": rs.slug},
            user=usr,
        )
        assert response.status_code == 403, "Non editor cannot get view"

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"slug": rs.slug},
        user=editor,
    )

    assert response.status_code == 200, "Editors can get view"


@pytest.mark.django_db
@override_settings(task_eager_propagates=True, task_always_eager=True)
def test_ground_truth_from_answers_workflow(
    client, django_capture_on_commit_callbacks
):
    rs = ReaderStudyFactory(is_educational=True)

    editor, reader, a_user = UserFactory.create_batch(3)
    rs.add_editor(editor)
    rs.add_reader(reader)

    ds = DisplaySetFactory(reader_study=rs)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    editor_answer = AnswerFactory(
        question=q,
        display_set=ds,
        creator=editor,
        answer=True,
    )
    reader_answer = AnswerFactory(
        question=q,
        display_set=ds,
        creator=reader,
        answer=True,
    )

    assert (
        not rs.has_ground_truth
    ), "Sanity: reader study starts without ground truth"
    assert reader_answer.score is None, "Sanity: score starts unassigned"

    # Copy answers
    for usr in [reader, a_user]:
        response = get_view_for_user(
            client=client,
            viewname="reader-studies:add-ground-truth-answers",
            reverse_kwargs={"slug": rs.slug},
            user=usr,
        )
        assert response.status_code == 403, "Readers and users cannot get form"

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:add-ground-truth-answers",
        reverse_kwargs={"slug": rs.slug},
        user=editor,
    )
    assert response.status_code == 200, "Editor can get form"

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            client=client,
            viewname="reader-studies:add-ground-truth-answers",
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            follow=True,
            data={"user": str(editor.pk)},
            user=editor,
        )
    assert response.status_code == 200, "Editor can post form"

    assert rs.has_ground_truth, "Sanity: reader study now has ground truth"
    assert not Answer.objects.filter(
        pk=editor_answer.pk,
        is_ground_truth=False,
    ).exists(), "Source answer is consumed"

    response = get_view_for_user(
        viewname="api:reader-study-ground-truth",
        reverse_kwargs={"pk": rs.pk, "case_pk": ds.pk},
        user=reader,
        client=client,
        content_type="application/json",
        follow=True,
    )
    assert response.status_code == 200, "Can retrieve ground truth"

    response = response.json()
    assert response[str(q.pk)]["answer"], "Ground truth is retrieved OK"

    reader_answer.refresh_from_db()
    assert reader_answer.score is not None, " Scores are assigned"

    # Finally, attempt to delete the ground truth
    response = get_view_for_user(
        viewname="reader-studies:ground-truth-delete",
        reverse_kwargs={"slug": rs.slug},
        user=editor,
        client=client,
        method=client.post,
    )
    assert response.status_code == 200, "Can remove ground truth"

    reader_answer.refresh_from_db()
    assert reader_answer.score is None, " Scores are unassigned"

    assert (
        not rs.has_ground_truth
    ), "Sanity: reader study no longer has ground truth"


@pytest.mark.parametrize(
    "accessible_to_readers, status_code",
    ([True, 200], [False, 403]),
)
@pytest.mark.django_db
def test_leaderboard_accessibility(client, accessible_to_readers, status_code):
    editor, reader, user = UserFactory.create_batch(3)
    rs = ReaderStudyFactory(
        is_educational=True,
        leaderboard_accessible_to_readers=accessible_to_readers,
    )
    rs.add_editor(editor)
    rs.add_reader(reader)

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:leaderboard",
        reverse_kwargs={"slug": rs.slug},
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:leaderboard",
        client=client,
        user=editor,
        reverse_kwargs={"slug": rs.slug},
    )
    assert response.status_code == 200

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:leaderboard",
        reverse_kwargs={"slug": rs.slug},
        user=reader,
    )
    assert response.status_code == status_code


@pytest.mark.django_db
def test_leaderboard_user_visibility(client):
    reader1, reader2, editor = UserFactory.create_batch(3)
    rs = ReaderStudyFactory(
        is_educational=True, leaderboard_accessible_to_readers=True
    )
    rs.add_editor(editor)
    rs.add_reader(reader1)
    rs.add_reader(reader2)

    reader1_userprofile_link = user_profile_link(reader1)
    reader2_userprofile_link = user_profile_link(reader2)

    qu = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.TEXT)
    AnswerFactory(creator=reader1, question=qu, answer="bar")
    AnswerFactory(creator=reader2, question=qu, answer="foo")
    AnswerFactory(question=qu, answer="bar", is_ground_truth=True)

    response = get_view_for_user(
        viewname="reader-studies:leaderboard",
        client=client,
        user=editor,
        reverse_kwargs={"slug": rs.slug},
    )
    html_for_editor = response.content.decode("utf-8")
    # editor sees user names
    assert response.status_code == 200
    assert reader1_userprofile_link in html_for_editor
    assert reader2_userprofile_link in html_for_editor

    response = get_view_for_user(
        viewname="reader-studies:leaderboard",
        client=client,
        user=reader1,
        reverse_kwargs={"slug": rs.slug},
    )
    html_for_reader1 = response.content.decode("utf-8")
    assert response.status_code == 200
    assert reader1_userprofile_link not in html_for_reader1
    assert reader2_userprofile_link not in html_for_reader1
    assert "<td> Reader </td>" in html_for_reader1
    assert "<td> You </td>" in html_for_reader1


@pytest.mark.django_db
def test_reader_study_launch_disabled_when_not_launchable(client):
    reader_study = ReaderStudyFactory()

    editor, reader = UserFactory.create_batch(2)
    reader_study.add_editor(editor)
    reader_study.add_reader(reader)

    assert reader_study.is_launchable

    for usr in [reader, editor]:
        response = get_view_for_user(
            client=client,
            viewname="reader-studies:detail",
            reverse_kwargs={"slug": reader_study.slug},
            user=usr,
        )
        assertContains(
            response, f'data-workstation-path="reader-study/{reader_study.pk}"'
        )

    reader_study.max_credits = 0
    reader_study.save()

    assert not reader_study.is_launchable

    for usr in [reader, editor]:
        response = get_view_for_user(
            client=client,
            viewname="reader-studies:detail",
            reverse_kwargs={"slug": reader_study.slug},
            user=usr,
        )
        assertNotContains(
            response, f'data-workstation-path="reader-study/{reader_study.pk}"'
        )


@pytest.mark.django_db
def test_civset_list_view_permissions(client):
    viewname = "reader-studies:display_sets"
    user, editor, reader = UserFactory.create_batch(3)
    reader_study = ReaderStudyFactory()
    reader_study.add_editor(editor)
    reader_study.add_reader(reader)
    ob1, ob2, ob3 = DisplaySetFactory.create_batch(
        3, **{"reader_study": reader_study}
    )
    ob4, ob5 = DisplaySetFactory.create_batch(2)

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=user,
        reverse_kwargs={"slug": reader_study.slug},
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=reader,
        reverse_kwargs={"slug": reader_study.slug},
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=editor,
        reverse_kwargs={"slug": reader_study.slug},
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 3
    for obj in [ob1, ob2, ob3]:
        assert obj in response.context["object_list"]
    for obj in [ob4, ob5]:
        assert obj not in response.context["object_list"]
