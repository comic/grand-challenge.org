import csv
import html
import io

import pytest
from actstream import action
from actstream.actions import is_following
from django.contrib.auth.models import Permission
from django.db.models import BLANK_CHOICE_DASH
from django.forms import HiddenInput, Select
from django.test import override_settings
from guardian.shortcuts import assign_perm

from grandchallenge.cases.widgets import FlexibleImageWidget
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.forms import SingleCIVForm
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.components.widgets import FlexibleFileWidget
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.reader_studies.forms import (
    AnswersFromGroundTruthForm,
    DisplaySetCreateForm,
    DisplaySetUpdateForm,
    GroundTruthFromAnswersForm,
    QuestionForm,
    ReaderStudyCreateForm,
)
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    Question,
    QuestionUserObjectPermission,
    QuestionWidgetKindChoices,
    ReaderStudy,
    ReaderStudyUserObjectPermission,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstation_configs.models import LookUpTable
from tests.anatomy_tests.factories import BodyStructureFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import (
    ImageFactory,
    ImagingModalityFactory,
    SessionFactory,
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.publications_tests.factories import PublicationFactory
from tests.reader_studies_tests import RESOURCE_PATH
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
    ReaderStudyPermissionRequestFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies, get_rs_creator
from tests.uploads_tests.factories import UserUploadFactory
from tests.utilization_tests.factories import SessionUtilizationFactory
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

    def try_create_rs(
        allow_case_navigation=False,
        shuffle_hanging_list=False,
        roll_over_answers_for_n_cases=0,
        public=True,
        description="",
        is_educational=False,
        instant_verification=False,
    ):
        return get_view_for_user(
            viewname="reader-studies:create",
            client=client,
            method=client.post,
            data={
                "title": "foo bar",
                "logo": uploaded_image(),
                "workstation": ws.pk,
                "allow_answer_modification": True,
                "shuffle_hanging_list": shuffle_hanging_list,
                "allow_case_navigation": allow_case_navigation,
                "access_request_handling": AccessRequestHandlingOptions.MANUAL_REVIEW,
                "roll_over_answers_for_n_cases": roll_over_answers_for_n_cases,
                "public": public,
                "description": description,
                "is_educational": is_educational,
                "instant_verification": instant_verification,
            },
            follow=True,
            user=creator,
        )

    response = try_create_rs()
    assert "error_1_id_workstation" in response.rendered_content

    # The editor must have view permissions for the workstation to add it
    ws.add_user(user=creator)

    roll_over_error = "Rolling over answers should not be used together with case navigation or shuffling of the hanging list"
    public_error = "Making a reader study public requires a description"
    for navigation, shuffle in [(True, True), (True, False), (False, True)]:
        response = try_create_rs(
            allow_case_navigation=navigation,
            shuffle_hanging_list=shuffle,
            roll_over_answers_for_n_cases=1,
        )
        assert "error_1_id_workstation" not in response.rendered_content
        assert roll_over_error in response.rendered_content
        assert public_error in response.rendered_content

    response = try_create_rs(roll_over_answers_for_n_cases=1)
    assert "error_1_id_workstation" not in response.rendered_content
    assert roll_over_error not in response.rendered_content
    assert public_error in response.rendered_content

    educational_error = "Reader study must be educational when instant verification is enabled."
    response = try_create_rs(is_educational=False, instant_verification=True)
    assert educational_error in response.rendered_content

    response = try_create_rs(
        roll_over_answers_for_n_cases=1,
        description="Some description",
        is_educational=True,
        instant_verification=True,
    )
    assert "error_1_id_workstation" not in response.rendered_content
    assert roll_over_error not in response.rendered_content
    assert public_error not in response.rendered_content
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
                "answer_type": AnswerType.TEXT,
                "widget": QuestionWidgetKindChoices.TEXT_INPUT,
                "order": 1,
                "image_port": "",
                "direction": "H",
                "options-TOTAL_FORMS": 0,
                "options-INITIAL_FORMS": 0,
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
        answer_type=Question.AnswerType.TEXT,
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
    assert question.answer_type == Question.AnswerType.TEXT
    assert question.direction == Question.Direction.HORIZONTAL
    assert question.order == 100
    assert question.interface is None

    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_SEGMENTATION,
        overlay_segments=[
            {"name": "s1", "visible": True, "voxel_value": 0},
            {"name": "s2", "visible": True, "voxel_value": 1},
        ],
    )
    form = QuestionForm(
        reader_study=question.reader_study,
        user=editor,
        instance=question,
        data={
            "question_text": "bar",
            "answer_type": Question.AnswerType.MASK,
            "direction": Question.Direction.VERTICAL,
            "overlay_segments": "["
            '{"name": "s1", "visible": true, "voxel_value": 0}'
            "]",
            "image_port": "M",
            "order": 200,
            "interface": str(ci.pk),
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
            "reader_study": question.reader_study.pk,
        },
    )
    with pytest.raises(ValueError):
        form.save()

    assert form.errors == {
        "__all__": [
            f"Overlay segments do not match those of {ci.title}. "
            'Please use [{"name": "s1", "visible": true, "voxel_value": 0}, '
            '{"name": "s2", "visible": true, "voxel_value": 1}].'
        ]
    }

    form = QuestionForm(
        reader_study=question.reader_study,
        user=editor,
        instance=question,
        data={
            "question_text": "bar",
            "answer_type": Question.AnswerType.MASK,
            "direction": Question.Direction.VERTICAL,
            "overlay_segments": "["
            '{"name": "s1", "visible": true, "voxel_value": 0},'
            '{"name": "s2", "visible": true, "voxel_value": 1}'
            "]",
            "image_port": "M",
            "order": 200,
            "interface": str(ci.pk),
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
            "reader_study": question.reader_study.pk,
        },
    )
    form.save()

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.AnswerType.MASK
    assert question.direction == Question.Direction.VERTICAL
    assert question.overlay_segments == [
        {"name": "s1", "visible": True, "voxel_value": 0},
        {"name": "s2", "visible": True, "voxel_value": 1},
    ]
    assert question.order == 200
    assert question.interface == ci

    AnswerFactory(question=question, answer="true")

    # An answer is added, so changing the question text or overlay segments
    # should no longer be possible
    form = QuestionForm(
        reader_study=question.reader_study,
        user=editor,
        instance=question,
        data={
            "question_text": "foo",
            "answer_type": Question.AnswerType.TEXT,
            "direction": Question.Direction.HORIZONTAL,
            "overlay_segments": '[{"name": "s1", "visible": true, "voxel_value": 0}]',
            "order": 100,
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
            "reader_study": question.reader_study.pk,
        },
    )
    form.save()

    question.refresh_from_db()
    assert question.question_text == "bar"
    assert question.answer_type == Question.AnswerType.MASK
    assert question.direction == Question.Direction.HORIZONTAL
    assert question.overlay_segments == [
        {"name": "s1", "visible": True, "voxel_value": 0},
        {"name": "s2", "visible": True, "voxel_value": 1},
    ]
    assert question.order == 100


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,interface_kind",
    (
        (AnswerType.TEXT, InterfaceKindChoices.STRING),
        (AnswerType.BOOL, InterfaceKindChoices.BOOL),
        (AnswerType.NUMBER, InterfaceKindChoices.FLOAT),
        (AnswerType.NUMBER, InterfaceKindChoices.INTEGER),
        (AnswerType.BOUNDING_BOX_2D, InterfaceKindChoices.TWO_D_BOUNDING_BOX),
        (
            AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
        ),
        (
            AnswerType.DISTANCE_MEASUREMENT,
            InterfaceKindChoices.DISTANCE_MEASUREMENT,
        ),
        (
            AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
        ),
        (AnswerType.POINT, InterfaceKindChoices.POINT),
        (AnswerType.MULTIPLE_POINTS, InterfaceKindChoices.MULTIPLE_POINTS),
        (AnswerType.POLYGON, InterfaceKindChoices.POLYGON),
        (AnswerType.MULTIPLE_POLYGONS, InterfaceKindChoices.MULTIPLE_POLYGONS),
        (AnswerType.LINE, InterfaceKindChoices.LINE),
        (AnswerType.MULTIPLE_LINES, InterfaceKindChoices.MULTIPLE_LINES),
        (AnswerType.ANGLE, InterfaceKindChoices.ANGLE),
        (AnswerType.MULTIPLE_ANGLES, InterfaceKindChoices.MULTIPLE_ANGLES),
        (AnswerType.CHOICE, InterfaceKindChoices.CHOICE),
        (AnswerType.MULTIPLE_CHOICE, InterfaceKindChoices.MULTIPLE_CHOICE),
        (AnswerType.MASK, InterfaceKindChoices.PANIMG_SEGMENTATION),
        (AnswerType.ELLIPSE, InterfaceKindChoices.ELLIPSE),
        (AnswerType.MULTIPLE_ELLIPSES, InterfaceKindChoices.MULTIPLE_ELLIPSES),
    ),
)
def test_question_form_interface_field(answer_type, interface_kind):
    ci = ComponentInterfaceFactory(kind=interface_kind)
    ci_img = ComponentInterface.objects.filter(
        kind=InterfaceKindChoices.PANIMG_IMAGE
    ).first()
    assert ci_img is not None
    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        initial={"answer_type": answer_type},
    )
    assert form.interface_choices().filter(pk=ci.pk).exists()
    assert not form.interface_choices().filter(pk=ci_img.pk).exists()


@pytest.mark.django_db
def test_question_form_interface_field_no_answer_type():
    assert ComponentInterface.objects.count() > 0
    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        initial={"answer_type": None},
    )
    # No answer_type provided, this happens for answers that already have
    # answers. The form shouldn't error and the interface_choices should
    # be empty.
    assert form.interface_choices().count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,port,questions_created",
    (
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
            "overlay_segments": "[]",
            "order": 1,
            "image_port": port,
            "direction": "H",
            "options-TOTAL_FORMS": 0,
            "options-INITIAL_FORMS": 0,
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


reader_study_copy_fields = ReaderStudy.copy_fields
reader_study_optional_copy_fields = set(ReaderStudy.optional_copy_fields)
reader_study_non_copy_fields = {
    "readerstudyuserobjectpermission",
    "readerstudygroupobjectpermission",
    "workstationsessionreaderstudy",
    "readerstudypermissionrequest",
    "optionalhangingprotocolreaderstudy",
    "session_utilizations",
    "sessionutilizationreaderstudy",
    "title",
    "description",
    "slug",
    "id",
    "created",
    "modified",
    "max_credits",
    "workstation_sessions",
    "actor_actions",
    "target_actions",
    "action_object_actions",
}


def test_reader_study_fields_copy_sets_disjoint():
    assert reader_study_copy_fields.isdisjoint(
        reader_study_optional_copy_fields
    )
    assert reader_study_copy_fields.isdisjoint(reader_study_non_copy_fields)
    assert reader_study_optional_copy_fields.isdisjoint(
        reader_study_non_copy_fields
    )


def test_all_reader_study_fields_defined_in_copy_sets():
    model = ReaderStudy
    union = (
        reader_study_copy_fields
        | reader_study_optional_copy_fields
        | reader_study_non_copy_fields
    )

    assert {f.name for f in model._meta.get_fields()} == union


# The `options` field is also copied but is not in the
# `copy_fields` list on the model because it is handled manually.
question_copy_fields = Question.copy_fields.union({"options"})
question_non_copy_fields = {
    "questionuserobjectpermission",
    "questiongroupobjectpermission",
    "answer",
    "id",
    "created",
    "modified",
    "reader_study",
}


def test_question_fields_copy_sets_disjoint():
    assert question_copy_fields.isdisjoint(question_non_copy_fields)


def test_all_question_fields_defined_in_copy_sets():
    model = Question
    union = question_copy_fields | question_non_copy_fields

    assert {f.name for f in model._meta.get_fields()} == union


@pytest.mark.django_db
def test_reader_study_copy_permission(client):
    rs = ReaderStudyFactory(title="original")
    admin = UserFactory()
    editor = UserFactory()
    reader = UserFactory()
    rs.add_editor(admin)
    rs.add_editor(editor)
    rs.add_reader(reader)
    add_perm = Permission.objects.get(
        codename=f"add_{ReaderStudy._meta.model_name}"
    )
    admin.user_permissions.add(add_perm)

    kwargs = dict(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"title": "copy"},
        follow=True,
    )

    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        user=reader,
        **kwargs,
    )

    assert response.status_code == 403
    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        user=editor,
        **kwargs,
    )

    assert response.status_code == 403
    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        user=admin,
        **kwargs,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 2

    rs_copy = ReaderStudy.objects.order_by("created").last()
    assert rs_copy.title == "copy"


def get_values(original, copy, field):
    try:
        accessor_name = field.get_accessor_name()
    except AttributeError:
        accessor_name = field.name
    original_value = getattr(original, accessor_name)
    value_in_copy = getattr(copy, accessor_name)
    return original_value, value_in_copy


def assert_value_copied(field, original_value, value_in_copy):
    if field.many_to_many or field.one_to_many:
        assert original_value.count() != 0
        assert value_in_copy.count() == original_value.count()
    else:
        assert original_value != field.default
        assert value_in_copy == original_value


def assert_value_not_copied(field, original_value, value_in_copy):
    if field.many_to_many or field.one_to_many:
        assert original_value.count() != 0
        assert value_in_copy.count() == 0
    else:
        assert original_value != field.default
        assert value_in_copy != original_value


@pytest.fixture
def reader_study_with_fields():
    rs = ReaderStudyFactory(
        title="original",
        workstation_config=WorkstationConfigFactory(),
        public=True,
        access_request_handling=AccessRequestHandlingOptions.ACCEPT_ALL,
        shuffle_hanging_list=True,
        is_educational=True,
        instant_verification=True,
        allow_answer_modification=True,
        enable_autosaving=True,
        allow_case_navigation=True,
        allow_show_all_annotations=True,
        roll_over_answers_for_n_cases=1,
        leaderboard_accessible_to_readers=True,
        max_credits=1,
    )
    rs.workstation_sessions.set([SessionFactory()])
    rs.optional_hanging_protocols.set([HangingProtocolFactory()])
    rs.publications.set([PublicationFactory()])
    rs.modalities.set([ImagingModalityFactory()])
    rs.structures.set([BodyStructureFactory()])
    rs.organizations.set([OrganizationFactory()])
    rs.session_utilizations.set([SessionUtilizationFactory()])
    ReaderStudyPermissionRequestFactory(reader_study=rs)
    reader = UserFactory()
    rs.add_reader(reader)
    action.send(rs, verb="started")
    action.send(reader, verb="joined", target=rs)
    action.send(reader, verb="has read", action_object=rs)

    return rs


@pytest.fixture
def copied_reader_study_with_fields(client, reader_study_with_fields):
    admin = UserFactory()
    reader_study_with_fields.add_editor(admin)
    add_perm = Permission.objects.get(
        codename=f"add_{ReaderStudy._meta.model_name}"
    )
    admin.user_permissions.add(add_perm)

    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": reader_study_with_fields.slug},
        data={"title": "copy"},
        user=admin,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 2

    copied_rs = ReaderStudy.objects.order_by("created").last()
    assert copied_rs.title == "copy"

    return copied_rs


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", reader_study_copy_fields)
def test_reader_study_copy_fields(
    reader_study_with_fields, copied_reader_study_with_fields, field_name
):
    field = ReaderStudy._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        reader_study_with_fields, copied_reader_study_with_fields, field
    )
    assert_value_copied(field, original_value, value_in_copy)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    reader_study_non_copy_fields.difference(
        ["readerstudygroupobjectpermission"]
    ),
)
def test_reader_study_non_copy_fields(
    reader_study_with_fields, copied_reader_study_with_fields, field_name
):
    if (
        field_name == "readerstudyuserobjectpermission"
        and len(ReaderStudyUserObjectPermission.allowed_permissions) == 0
    ):
        pytest.xfail(
            reason="Cannot test if copied or not if no possible value"
        )

    field = ReaderStudy._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        reader_study_with_fields, copied_reader_study_with_fields, field
    )

    assert_value_not_copied(field, original_value, value_in_copy)


@pytest.mark.django_db
def test_reader_study_non_copy_field_readerstudygroupobjectpermission(
    reader_study_with_fields, copied_reader_study_with_fields
):
    field_name = "readerstudygroupobjectpermission"
    field = ReaderStudy._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        reader_study_with_fields, copied_reader_study_with_fields, field
    )

    assert value_in_copy.count() == 10
    assert set(value_in_copy.all()).isdisjoint(original_value.all())


@pytest.fixture()
def reader_study_with_optional_fields():
    images = ImageFactory.create_batch(2)
    civs = []
    interfaces = []
    for im in images:
        civ = ComponentInterfaceValueFactory(image=im)
        civs.append(civ)
        interfaces.append(civ.interface.slug)
    rs = ReaderStudyFactory(
        title="original",
        case_text={images[0].name: "test", images[1].name: "test2"},
        view_content={"main": interfaces[0], "secondary": interfaces[1]},
        hanging_protocol=HangingProtocolFactory(),
    )
    rs.optional_hanging_protocols.set([HangingProtocolFactory()])
    for index in range(2):
        ds = DisplaySetFactory(
            reader_study=rs,
            title=f"display set title {index}",
            order=index,
        )
        ds.values.add(civs[index])
    QuestionFactory(reader_study=rs)
    editor = UserFactory()
    reader = UserFactory()
    rs.add_editor(editor)
    rs.add_reader(reader)

    return rs


def copy_reader_study_with_optional_field(
    settings,
    client,
    django_capture_on_commit_callbacks,
    reader_study,
    field_name,
):
    settings.task_eager_propagates = True
    settings.task_always_eager = True

    admin = UserFactory()
    reader_study.add_editor(admin)
    add_perm = Permission.objects.get(
        codename=f"add_{ReaderStudy._meta.model_name}"
    )
    admin.user_permissions.add(add_perm)

    assert ReaderStudy.objects.count() == 1

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:copy",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": reader_study.slug},
            data={"title": "copy", f"copy_{field_name}": True},
            user=admin,
            follow=True,
        )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 2

    copied_rs = ReaderStudy.objects.order_by("created").last()
    assert copied_rs.title == "copy"

    return copied_rs


@pytest.mark.django_db
@pytest.mark.parametrize(
    "optional_field_name", reader_study_optional_copy_fields
)
def test_reader_study_copy_all_optional_fields_implemented(
    settings,
    client,
    django_capture_on_commit_callbacks,
    reader_study_with_optional_fields,
    optional_field_name,
):
    copied_reader_study = copy_reader_study_with_optional_field(
        settings=settings,
        client=client,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
        reader_study=reader_study_with_optional_fields,
        field_name=optional_field_name,
    )

    # assert specified optional field has been copied
    field = ReaderStudy._meta.get_field(optional_field_name)
    original_value, value_in_copy = get_values(
        reader_study_with_optional_fields, copied_reader_study, field
    )

    if optional_field_name == "readers_group":
        assert original_value.user_set.count() == 1
        assert (
            value_in_copy.user_set.count() == original_value.user_set.count()
        )
    elif optional_field_name == "editors_group":
        assert original_value.user_set.count() == 2
        assert (
            value_in_copy.user_set.count() == original_value.user_set.count()
        )
    else:
        assert_value_copied(field, original_value, value_in_copy)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "optional_field_name_copied", reader_study_optional_copy_fields
)
@pytest.mark.parametrize(
    "optional_field_name_not_copied", reader_study_optional_copy_fields
)
def test_reader_study_copy_selected_optional_field_only(
    settings,
    client,
    django_capture_on_commit_callbacks,
    reader_study_with_optional_fields,
    optional_field_name_copied,
    optional_field_name_not_copied,
):
    copied_reader_study = copy_reader_study_with_optional_field(
        settings=settings,
        client=client,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
        reader_study=reader_study_with_optional_fields,
        field_name=optional_field_name_copied,
    )

    if optional_field_name_not_copied == optional_field_name_copied:
        return

    field = ReaderStudy._meta.get_field(optional_field_name_not_copied)
    original_value, value_in_copy = get_values(
        reader_study_with_optional_fields, copied_reader_study, field
    )

    if optional_field_name_not_copied == "readers_group":
        assert original_value.user_set.count() == 1
        assert value_in_copy.user_set.count() == 0
    elif optional_field_name_not_copied == "editors_group":
        assert original_value.user_set.count() == 2
        assert value_in_copy.user_set.count() == 1
    else:
        assert_value_not_copied(field, original_value, value_in_copy)


@pytest.fixture()
def reader_study_with_question():
    rs = ReaderStudyFactory(title="original")
    editor = UserFactory()
    reader = UserFactory()
    rs.add_reader(reader)
    rs.add_editor(editor)
    lut = LookUpTable.objects.create(
        title="foo",
        color="[1 2 3 4, 5 6 7 8]",
        alpha="[1 1, 1 1]",
        color_invert="[1 2 3 4, 5 6 7 8]",
        alpha_invert="[1 1, 1 1, 1 1]",
    )
    question = QuestionFactory(
        reader_study=rs,
        question_text="question 1",
        help_text="Some help text",
        answer_type=Question.AnswerType.NUMBER,
        image_port=Question.ImagePort.MAIN,
        required=False,
        direction=Question.Direction.VERTICAL,
        scoring_function=Question.ScoringFunction.ACCURACY,
        order=324,
        interface=ComponentInterfaceFactory(),
        overlay_segments={"foo": "bar"},
        look_up_table=lut,
        widget=QuestionWidgetKindChoices.NUMBER_INPUT,
        answer_max_value=20,
        answer_min_value=1,
        answer_step_size=0.5,
        answer_min_length=1,
        answer_max_length=3,
        answer_match_pattern=r"^hello world$",
        default_annotation_color="#FF0000",
        empty_answer_confirmation=True,
        empty_answer_confirmation_label="test",
    )
    CategoricalOptionFactory(question=question, title="option1")
    AnswerFactory(question=question)
    return rs


@pytest.fixture()
def copied_question(client, reader_study_with_question):
    admin = UserFactory()
    reader_study_with_question.add_editor(admin)
    add_perm = Permission.objects.get(
        codename=f"add_{ReaderStudy._meta.model_name}"
    )
    admin.user_permissions.add(add_perm)

    assert ReaderStudy.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:copy",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": reader_study_with_question.slug},
        data={"title": "copy", "copy_questions": True},
        user=admin,
        follow=True,
    )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 2

    copied_rs = ReaderStudy.objects.order_by("created").last()
    assert copied_rs.title == "copy"
    assert copied_rs.questions.count() == 1

    question = reader_study_with_question.questions.first()
    copied_question = copied_rs.questions.first()

    assert copied_question.pk != question.pk
    assert copied_question.reader_study != question.reader_study

    return copied_question


@pytest.mark.django_db
@pytest.mark.parametrize("field_name", question_copy_fields)
def test_reader_study_copy_question_copy_fields(
    reader_study_with_question, copied_question, field_name
):
    if (
        field_name == "scoring_function"
        and len(Question.SCORING_FUNCTIONS) == 1
    ):
        pytest.xfail(
            reason="Cannot test if copied or not if only one possible value"
        )

    question = reader_study_with_question.questions.first()
    field = Question._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        question, copied_question, field
    )

    assert_value_copied(field, original_value, value_in_copy)


@pytest.mark.django_db
def test_reader_study_copy_question_options(
    reader_study_with_question, copied_question
):
    question = reader_study_with_question.questions.first()

    assert copied_question.options.get().title == question.options.get().title
    assert copied_question.options.get().pk != question.options.get().pk


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name",
    question_non_copy_fields.difference(["questiongroupobjectpermission"]),
)
def test_reader_study_copy_questions_non_copy_fields(
    reader_study_with_question, copied_question, field_name
):
    if (
        field_name == "questionuserobjectpermission"
        and len(QuestionUserObjectPermission.allowed_permissions) == 0
    ):
        pytest.xfail(
            reason="Cannot test if copied or not if no possible value"
        )

    question = reader_study_with_question.questions.first()
    field = Question._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        question, copied_question, field
    )

    assert_value_not_copied(field, original_value, value_in_copy)


@pytest.mark.django_db
def test_reader_study_copy_questions_non_copy_questiongroupobjectpermission(
    reader_study_with_question, copied_question
):
    question = reader_study_with_question.questions.first()
    field_name = "questiongroupobjectpermission"
    field = Question._meta.get_field(field_name)
    original_value, value_in_copy = get_values(
        question, copied_question, field
    )

    assert value_in_copy.count() == 2
    assert set(value_in_copy.all()).isdisjoint(original_value.all())


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
def test_reader_study_add_ground_truth_csv(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    q = QuestionFactory(
        reader_study=rs,
        question_text="bar",
        answer_type=Question.AnswerType.TEXT,
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
    q3 = QuestionFactory(
        reader_study=rs,
        question_text="choice_optional",
        answer_type=Question.AnswerType.CHOICE,
        required=False,
    )
    options = {}
    for i, q_ in enumerate([q1, q2, q3]):
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
    ds1 = DisplaySetFactory(
        reader_study=rs, pk="00000000-0000-0000-0000-0000000000d1"
    )
    ds2 = DisplaySetFactory(
        reader_study=rs, pk="00000000-0000-0000-0000-0000000000d2"
    )
    ds3 = DisplaySetFactory(
        reader_study=rs, pk="00000000-0000-0000-0000-0000000000d3"
    )

    civ = ComponentInterfaceValueFactory(image=im1)
    ds1.values.add(civ)

    civ = ComponentInterfaceValueFactory(image=im2)
    ds2.values.add(civ)

    civ = ComponentInterfaceValueFactory(image=im3)
    ds3.values.add(civ)
    civ = ComponentInterfaceValueFactory(image=im4)
    ds3.values.add(civ)

    editor = UserFactory()
    reader = UserFactory()
    rs.editors_group.user_set.add(editor)
    rs.readers_group.user_set.add(reader)

    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth-csv",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=reader,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth-csv",
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
            viewname="reader-studies:add-ground-truth-csv",
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

    with open(RESOURCE_PATH / "ground_truth_invalid.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth-csv",
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
            viewname="reader-studies:add-ground-truth-csv",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"ground_truth": gt},
            follow=True,
            user=editor,
        )
    assert response.status_code == 200

    answer_count = 12  # 4 questions * 3 ds (q3 is optional and has no gt)
    assert Answer.objects.all().count() == answer_count
    assert Answer.objects.filter(is_ground_truth=True).count() == answer_count
    assert Answer.objects.get(display_set=ds1, question=q).answer == "yes"
    assert (
        Answer.objects.get(display_set=ds1, question=q).explanation
        == "explanation, with a comma"
    )
    assert Answer.objects.get(display_set=ds2, question=q).explanation == ""
    assert Answer.objects.get(display_set=ds1, question=q0).answer is True
    assert (
        Answer.objects.get(display_set=ds1, question=q1).answer
        == options["0-1"].pk
    )
    assert sorted(
        Answer.objects.get(display_set=ds1, question=q2).answer
    ) == sorted([options["1-1"].pk, options["1-2"].pk])

    with open(RESOURCE_PATH / "ground_truth_new.csv") as gt:
        response = get_view_for_user(
            viewname="reader-studies:add-ground-truth-csv",
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
    assert Answer.objects.get(display_set=ds1, question=q).answer == "no"
    assert (
        Answer.objects.get(display_set=ds1, question=q).explanation
        == "new explanation"
    )
    assert Answer.objects.get(display_set=ds1, question=q).creator == editor
    assert (
        Answer.objects.get(display_set=ds2, question=q).explanation
        == "explanation"
    )
    assert Answer.objects.get(display_set=ds1, question=q0).answer is False
    assert (
        Answer.objects.get(display_set=ds1, question=q1).answer
        == options["0-2"].pk
    )
    assert Answer.objects.get(display_set=ds1, question=q2).answer == [
        options["1-0"].pk
    ]


@pytest.mark.django_db
def test_reader_study_add_ground_truth_ds(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    QuestionFactory(
        reader_study=rs,
        question_text="bar",
        answer_type=Question.AnswerType.TEXT,
    )

    civ = ComponentInterfaceValueFactory(image=ImageFactory())
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

    editor = UserFactory()
    rs.editors_group.user_set.add(editor)

    gt = io.StringIO()
    fake_writer = csv.writer(gt)
    fake_writer.writerows([["images", "foo"], [str(ds.pk), "bar"]])
    gt.seek(0)

    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth-csv",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"ground_truth": gt},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_class",
    (
        DisplaySetCreateForm,
        DisplaySetUpdateForm,
    ),
)
def test_display_set_update_form(form_class):
    rs = ReaderStudyFactory()
    user = UserFactory()
    rs.add_editor(user)
    ds = DisplaySetFactory(reader_study=rs)

    for slug, store_in_db in [("slug-1", False), ("slug-2", True)]:
        ci = ComponentInterfaceFactory(
            title=slug,
            kind=InterfaceKindChoices.ANY,
            store_in_database=store_in_db,
        )
        civ = ComponentInterfaceValueFactory(interface=ci)
        ds.values.add(civ)

    instance = None if form_class == DisplaySetCreateForm else ds
    form = form_class(user=user, instance=instance, base_obj=rs)
    assert sorted(form.fields.keys()) == [
        f"{INTERFACE_FORM_FIELD_PREFIX}slug-1",
        f"{INTERFACE_FORM_FIELD_PREFIX}slug-2",
        "order",
        "title",
    ]
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}slug-1"].widget,
        FlexibleFileWidget,
    )
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}slug-2"].widget,
        JSONEditorWidget,
    )

    ci = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.STRING, title="slug-3"
    )
    QuestionFactory(reader_study=rs, answer_type=AnswerType.TEXT, interface=ci)
    del rs.linked_component_interfaces
    form = form_class(user=user, instance=instance, base_obj=rs)
    assert sorted(form.fields.keys()) == [
        f"{INTERFACE_FORM_FIELD_PREFIX}slug-1",
        f"{INTERFACE_FORM_FIELD_PREFIX}slug-2",
        f"{INTERFACE_FORM_FIELD_PREFIX}slug-3",
        "order",
        "title",
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_class",
    (DisplaySetCreateForm, DisplaySetUpdateForm),
)
def test_display_set_form_unique_title(form_class):
    rs1 = ReaderStudyFactory()

    user = UserFactory()
    rs1.add_editor(user)

    ds1 = DisplaySetFactory(reader_study=rs1, title="Title in reader study 1")

    instance1 = None
    if form_class == DisplaySetUpdateForm:
        instance1 = DisplaySetFactory(reader_study=rs1)

    # Adding a unique title in reader study 1 is allowed
    form = form_class(
        user=user,
        instance=instance1,
        base_obj=rs1,
        data={
            "title": "A unique title",
            "order": 10,
        },
    )
    assert form.is_valid()

    # Adding an existing title in reader study 1 is not allowed
    form = form_class(
        user=user,
        instance=instance1,
        base_obj=rs1,
        data={
            "title": ds1.title,
            "order": 10,
        },
    )
    assert not form.is_valid()

    # However, it is allowed if it's in another archive all together
    rs2 = ReaderStudyFactory()
    rs2.add_editor(user)

    instance2 = None
    if form_class == DisplaySetUpdateForm:
        instance2 = DisplaySetFactory(reader_study=rs2)

    form = form_class(
        user=user,
        instance=instance2,
        base_obj=rs2,
        data={
            "title": ds1.title,
            "order": 10,
        },
    )
    assert form.is_valid()


@pytest.mark.parametrize(
    "form_class",
    (
        DisplaySetCreateForm,
        DisplaySetUpdateForm,
    ),
)
@pytest.mark.django_db
def test_display_set_form_interface_fields_not_required(form_class):
    rs = ReaderStudyFactory()
    user = UserFactory()
    rs.add_editor(user)
    ci_img = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)
    ci_file = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    for ci in [ci_img, ci_file, ci_str]:
        civ = ComponentInterfaceValueFactory(interface=ci)
        ds = DisplaySetFactory(reader_study=rs)
        ds.values.add(civ)

    instance = None if form_class == DisplaySetCreateForm else ds
    form = form_class(user=user, instance=instance, base_obj=rs)
    for name, field in form.fields.items():
        if not name == "order":
            assert not field.required


@pytest.mark.django_db
def test_display_set_update_form_image_field_queryset_filters():
    rs = ReaderStudyFactory()
    user = UserFactory()
    rs.add_editor(user)
    ci_img = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_IMAGE,
        title="image",
    )
    im1, im2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", user, im1)
    upload1 = UserUploadFactory(creator=user)
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    upload2 = UserUploadFactory()
    civ_img = ComponentInterfaceValueFactory(interface=ci_img)
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ_img)
    form = DisplaySetUpdateForm(user=user, instance=ds, base_obj=rs)
    assert (
        im1
        in form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}image"]
        .fields[0]
        .queryset.all()
    )
    assert (
        im2
        not in form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}image"]
        .fields[0]
        .queryset.all()
    )
    assert (
        upload1
        in form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}image"]
        .fields[1]
        .queryset.all()
    )
    assert (
        upload2
        not in form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}image"]
        .fields[1]
        .queryset.all()
    )


@pytest.mark.django_db
def test_display_set_add_interface_form():
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    user = UserFactory()
    rs.add_editor(user)

    ci_file = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )
    ci_value = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=True
    )
    ci_image = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.PANIMG_IMAGE, store_in_database=False
    )

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=None,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == ["interface-1"]

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=ci_file.pk,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == [
        f"{INTERFACE_FORM_FIELD_PREFIX}{ci_file.slug}",
        "interface",
    ]
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_file.slug}"].widget,
        FlexibleFileWidget,
    )

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=ci_value.pk,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == [
        f"{INTERFACE_FORM_FIELD_PREFIX}{ci_value.slug}",
        "interface",
    ]
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_value.slug}"].widget,
        JSONEditorWidget,
    )

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=ci_image.pk,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == [
        f"{INTERFACE_FORM_FIELD_PREFIX}{ci_image.slug}",
        "interface",
    ]
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_image.slug}"].widget,
        FlexibleImageWidget,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, choices",
    (
        (
            AnswerType.TEXT,
            [("TEXT_INPUT", "Text Input"), ("TEXT_AREA", "Text Area")],
        ),
        (AnswerType.BOOL, BLANK_CHOICE_DASH),
        (
            AnswerType.NUMBER,
            [
                BLANK_CHOICE_DASH[0],
                ("NUMBER_INPUT", "Number Input"),
                ("NUMBER_RANGE", "Number Range"),
            ],
        ),
        (AnswerType.POINT, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_POINTS,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.BOUNDING_BOX_2D, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.DISTANCE_MEASUREMENT, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.POLYGON, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_POLYGONS,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.LINE, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_LINES,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.ANGLE, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_ANGLES,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (AnswerType.ELLIPSE, BLANK_CHOICE_DASH),
        (
            AnswerType.MULTIPLE_ELLIPSES,
            [
                BLANK_CHOICE_DASH[0],
                ("ACCEPT_REJECT", "Accept/Reject Findings"),
            ],
        ),
        (
            AnswerType.CHOICE,
            [
                ("RADIO_SELECT", "Radio Select"),
                ("SELECT", "Select"),
            ],
        ),
        (
            AnswerType.MULTIPLE_CHOICE,
            [
                BLANK_CHOICE_DASH[0],
                ("CHECKBOX_SELECT_MULTIPLE", "Checkbox Select Multiple"),
                ("SELECT_MULTIPLE", "Select Multiple"),
            ],
        ),
        (None, BLANK_CHOICE_DASH),
        (AnswerType.MASK, BLANK_CHOICE_DASH),
    ),
)
def test_question_form_answer_widget_choices(answer_type, choices):
    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        initial=(
            {"answer_type": answer_type} if answer_type is not None else {}
        ),
    )
    assert form.widget_choices() == choices


@pytest.mark.django_db
def test_question_form_initial_widget():
    qu = QuestionFactory(answer_type=AnswerType.TEXT)
    form = QuestionForm(
        reader_study=ReaderStudyFactory(), user=UserFactory(), instance=qu
    )
    assert not form.initial_widget()

    qu.widget = QuestionWidgetKindChoices.ACCEPT_REJECT
    form2 = QuestionForm(
        reader_study=ReaderStudyFactory(), user=UserFactory(), instance=qu
    )
    assert form2.initial_widget() == QuestionWidgetKindChoices.ACCEPT_REJECT


@pytest.mark.django_db
def test_question_widget_choices_for_non_editable_instance():
    # no matter whether the question is editable, widget choices should be the same
    qu = QuestionFactory(answer_type=AnswerType.TEXT)
    form = QuestionForm(
        reader_study=ReaderStudyFactory(), user=UserFactory(), instance=qu
    )
    assert form.widget_choices() == [
        ("TEXT_INPUT", "Text Input"),
        ("TEXT_AREA", "Text Area"),
    ]
    AnswerFactory(question=qu, answer="Foo")
    form = QuestionForm(
        reader_study=ReaderStudyFactory(), user=UserFactory(), instance=qu
    )
    assert form.widget_choices() == [
        ("TEXT_INPUT", "Text Input"),
        ("TEXT_AREA", "Text Area"),
    ]


@pytest.mark.django_db
def test_question_default_annotation_color():
    default_options = {
        "direction": Question.Direction.HORIZONTAL,
        "order": 100,
        "question_text": "gfda",
        "options-TOTAL_FORMS": 0,
        "options-INITIAL_FORMS": 0,
        "options-MIN_NUM_FORMS": 0,
        "options-MAX_NUM_FORMS": 1000,
    }

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            **default_options,
            "default_annotation_color": "#000000",
        },
    )

    assert form.is_valid() is False
    assert form.errors == {
        "__all__": [
            "Default annotation color should only be set for annotation questions"
        ]
    }

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.MASK,
            "image_port": Question.ImagePort.MAIN,
            **default_options,
            "default_annotation_color": "#000000",
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            **default_options,
            "default_annotation_color": "",
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            **default_options,
            "default_annotation_color": None,
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            **default_options,
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
        data={
            "answer_type": AnswerType.MASK,
            "image_port": Question.ImagePort.MAIN,
            **default_options,
            "default_annotation_color": "#000",
        },
    )
    assert form.is_valid() is False
    assert form.errors == {
        "default_annotation_color": [
            "This is an invalid color code. It must be an HTML hexadecimal color code e.g. #000000"
        ]
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "formset_data,expected_errors",
    (
        (
            {
                "options-TOTAL_FORMS": 0,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
            },
            {
                "__all__": [
                    "At least one option should be supplied for (multiple) choice questions"
                ],
            },
        ),
        (
            {
                "options-TOTAL_FORMS": 1,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "",
                "options-0-default": False,
            },
            {
                "__all__": [
                    "At least one option should be supplied for (multiple) choice questions"
                ],
            },
        ),
        (
            {
                "options-TOTAL_FORMS": 1,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": False,
            },
            {},
        ),
        (
            {
                "options-TOTAL_FORMS": 2,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": False,
                "options-1-title": "",
                "options-1-default": False,
            },
            {},
        ),
        (
            {
                "options-TOTAL_FORMS": 2,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": True,
                "options-1-title": "",
                "options-1-default": True,
            },
            {},
        ),
        (
            {
                "options-TOTAL_FORMS": 2,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": True,
                "options-1-title": "baz",
                "options-1-default": True,
            },
            {
                "__all__": ["Only one option can be set as default"],
            },
        ),
        (
            {
                "options-TOTAL_FORMS": 3,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": True,
                "options-1-title": "",
                "options-1-default": True,
                "options-2-title": "baz",
                "options-2-default": False,
            },
            {},  # 2nd form is ignored as it is empty
        ),
        (
            {
                "options-TOTAL_FORMS": 2,
                "options-INITIAL_FORMS": 0,
                "options-MIN_NUM_FORMS": 0,
                "options-MAX_NUM_FORMS": 1000,
                "options-0-title": "bar",
                "options-0-default": True,
                "options-1-title": "baz",
                "options-1-default": True,
                "options-1-DELETE": True,
            },
            {},  # 2nd form is ignored as it is deleted
        ),
    ),
)
def test_question_create_options_validation(formset_data, expected_errors):
    parent_data = {
        "question_text": "foo",
        "answer_type": AnswerType.CHOICE,
        "direction": Question.Direction.HORIZONTAL,
        "order": 10,
        "widget": QuestionWidgetKindChoices.RADIO_SELECT,
    }

    form = QuestionForm(
        data={**parent_data, **formset_data},
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
    )

    form.is_valid()
    assert form.errors == expected_errors


@pytest.mark.django_db
def test_question_choices_are_created():
    form = QuestionForm(
        data={
            "question_text": "foo",
            "answer_type": AnswerType.CHOICE,
            "direction": Question.Direction.HORIZONTAL,
            "order": 10,
            "widget": QuestionWidgetKindChoices.RADIO_SELECT,
            "options-TOTAL_FORMS": 3,
            "options-INITIAL_FORMS": 0,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
            "options-0-title": "bar",
            "options-0-default": True,
            "options-1-title": "",
            "options-1-default": False,
            "options-2-title": "baz",
            "options-2-default": False,
        },
        reader_study=ReaderStudyFactory(),
        user=UserFactory(),
    )

    form.is_valid()
    form.save()

    question = Question.objects.get()
    options = question.options.all()

    assert options.count() == 2
    assert options[0].title == "bar"
    assert options[0].default is True
    assert options[1].title == "baz"
    assert options[1].default is False


@pytest.mark.django_db
def test_option_cannot_be_deleted():
    q = QuestionFactory(answer_type=AnswerType.CHOICE, question_text="foo")
    c = CategoricalOptionFactory(question=q, title="old", default=False)
    AnswerFactory(question=q, answer=c.pk)

    form = QuestionForm(
        reader_study=q.reader_study,
        user=UserFactory(),
        data={
            "question_text": q.question_text,
            "answer_type": AnswerType.CHOICE,
            "direction": Question.Direction.HORIZONTAL,
            "order": 10,
            "widget": QuestionWidgetKindChoices.RADIO_SELECT,
            "options-TOTAL_FORMS": 2,
            "options-INITIAL_FORMS": 1,
            "options-MIN_NUM_FORMS": 0,
            "options-MAX_NUM_FORMS": 1000,
            "options-0-title": "new",
            "options-0-default": True,
            "options-0-id": c.pk,
            "options-0-DELETE": True,
            "options-1-title": "bar",
            "options-1-default": True,
        },
    )

    form.is_valid()
    assert form.errors == {}

    form.save()

    # Data should be unchanged
    c.refresh_from_db()
    assert c.title == "old"
    assert c.default is False

    # 2nd form should be ignored
    assert q.options.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, choices",
    (
        (
            AnswerType.MASK,
            [
                (
                    InteractiveAlgorithmChoices.ULS23_BASELINE.value,
                    InteractiveAlgorithmChoices.ULS23_BASELINE.label,
                )
            ],
        ),
        *[
            (answer_type, [])
            for answer_type in AnswerType.values
            if answer_type != AnswerType.MASK
        ],
    ),
)
def test_question_form_interactive_algorithm_field(answer_type, choices):
    user_with_permission, user_without_perm = UserFactory.create_batch(2)
    assign_perm(
        "reader_studies.add_interactive_algorithm_to_question",
        user_with_permission,
    )

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=user_without_perm,
        initial={"answer_type": answer_type},
    )
    assert form.interactive_algorithm_choices() == [*BLANK_CHOICE_DASH]
    assert form.fields["interactive_algorithm"].disabled
    assert isinstance(form.fields["interactive_algorithm"].widget, HiddenInput)

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        user=user_with_permission,
        initial={"answer_type": answer_type},
    )
    assert form.interactive_algorithm_choices() == [
        *BLANK_CHOICE_DASH,
        *choices,
    ]
    assert not form.fields["interactive_algorithm"].disabled
    assert isinstance(form.fields["interactive_algorithm"].widget, Select)


@pytest.mark.django_db
def test_interactive_algorithm_field_permissions():
    editor, editor_with_permission = UserFactory.create_batch(2)
    rs = ReaderStudyFactory()

    rs.add_editor(editor)
    rs.add_editor(editor_with_permission)

    assign_perm(
        "reader_studies.add_interactive_algorithm_to_question",
        editor_with_permission,
    )

    form = QuestionForm(
        reader_study=rs,
        user=editor,
        data={
            "question_text": "foo",
            "answer_type": Question.AnswerType.MASK,
            "interactive_algorithm": InteractiveAlgorithmChoices.ULS23_BASELINE,
        },
    )
    form.is_valid()
    assert form.cleaned_data["interactive_algorithm"] == ""

    form = QuestionForm(
        reader_study=rs,
        user=editor_with_permission,
        data={
            "question_text": "foo",
            "answer_type": Question.AnswerType.MASK,
            "interactive_algorithm": InteractiveAlgorithmChoices.ULS23_BASELINE,
        },
    )
    form.is_valid()
    assert (
        form.cleaned_data["interactive_algorithm"]
        == InteractiveAlgorithmChoices.ULS23_BASELINE
    )


@pytest.mark.django_db
@override_settings(task_eager_propagates=True, task_always_eager=True)
def test_answers_from_ground_truth_form(django_capture_on_commit_callbacks):
    rs = ReaderStudyFactory()

    reader, other_reader = UserFactory.create_batch(2)
    rs.add_reader(other_reader)
    rs.add_reader(reader)

    ds1 = DisplaySetFactory(reader_study=rs)
    ds2 = DisplaySetFactory(reader_study=rs)

    q1 = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    q2 = QuestionFactory(
        reader_study=rs,
        question_text="q2",
        answer_type=Question.AnswerType.BOOL,
    )

    # Create ground truth
    AnswerFactory(
        question=q1,
        display_set=ds1,
        creator=other_reader,
        answer=False,
        is_ground_truth=True,
    )
    AnswerFactory(
        question=q2,
        display_set=ds1,
        creator=reader,  # Note, mixing creators here for testing purposes
        answer=False,
        is_ground_truth=True,
    )

    reader_answer = AnswerFactory(
        question=q1,
        display_set=ds2,
        creator=reader,
        answer=True,
        is_ground_truth=False,
    )

    other_reader_answer = AnswerFactory(
        question=q1,
        display_set=ds1,
        creator=other_reader,
        answer=False,
        is_ground_truth=False,
    )

    form = AnswersFromGroundTruthForm(
        reader_study=rs,
        request_user=other_reader,
    )
    assert not form.is_valid(), "Can't push answers with answer present"

    other_reader_answer.delete()

    form = AnswersFromGroundTruthForm(
        reader_study=rs,
        request_user=other_reader,
        data={},
    )
    assert form.is_valid(), "Can now push answers"

    with django_capture_on_commit_callbacks(execute=True):
        form.schedule_answers_from_ground_truth_task()

    reader_answer.refresh_from_db()

    a1 = Answer.objects.get(
        display_set=ds1,
        question=q1,
        is_ground_truth=False,
    )
    a2 = Answer.objects.get(
        display_set=ds1,
        question=q2,
        is_ground_truth=False,
    )

    # Check permissions
    for answer in [a1, a2]:
        assert answer.creator == other_reader, "Correct creator"
        for perm in ["view_answer", "change_answer"]:
            assert other_reader.has_perm(perm, answer)
            assert not reader.has_perm(perm, answer)

    assert rs.has_ground_truth, "Sanity: Ground Truth is intact"


@pytest.mark.django_db
@override_settings(task_eager_propagates=True, task_always_eager=True)
def test_ground_truth_from_answers_form(django_capture_on_commit_callbacks):
    rs = ReaderStudyFactory()

    reader, editor = UserFactory.create_batch(2)
    rs.add_editor(editor)
    rs.add_reader(reader)

    ds = DisplaySetFactory(reader_study=rs)
    q1 = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    q2 = QuestionFactory(
        reader_study=rs,
        question_text="q2",
        answer_type=Question.AnswerType.BOOL,
    )

    scored_answer = AnswerFactory(
        question=q1, display_set=ds, creator=reader, answer=True
    )
    assert scored_answer.score is None, "Sanity: answer starts without a score"

    # Not ground truth applicable
    AnswerFactory(
        question=QuestionFactory(
            reader_study=rs,
            question_text="BB",
            answer_type=Question.AnswerType.BOUNDING_BOX_2D,
        ),
        display_set=ds,
        creator=editor,
        answer="Foo",
    )

    form = GroundTruthFromAnswersForm(
        reader_study=rs,
        data={"user": str(reader.pk)},
    )
    assert not form.is_valid()

    # Answer 1 of 2 questions
    AnswerFactory(question=q1, display_set=ds, creator=editor, answer=True)

    form = GroundTruthFromAnswersForm(
        reader_study=rs,
        data={"user": str(reader.pk)},
    )
    assert (
        not form.is_valid()
    ), "With only one answer the user is a valid source"

    # Answer 2 of 2 questions
    AnswerFactory(question=q2, display_set=ds, creator=editor, answer=True)

    form = GroundTruthFromAnswersForm(
        reader_study=rs,
        data={"user": str(editor.pk)},
    )
    assert form.is_valid(), "With both answers the user is a valid source"

    with django_capture_on_commit_callbacks(execute=True):
        form.create_ground_truth()

    assert not Answer.objects.filter(
        question__answer_type=Question.AnswerType.BOUNDING_BOX_2D,
        is_ground_truth=True,
    ).exists(), "Non applicable gt answer did not get copied"

    scored_answer.refresh_from_db()
    assert scored_answer.score == 1.0, "Existing answers are scored"

    form = GroundTruthFromAnswersForm(
        reader_study=rs,
        data={"user": str(editor.pk)},
    )
    assert (
        not form.is_valid()
    ), "With existing ground truth, the form is no longer valid"


@pytest.mark.django_db
def test_leaderboard_accessible_to_readers_only_for_educational_rs():
    user = UserFactory()
    form = ReaderStudyCreateForm(
        user=user,
        data={
            "roll_over_answers_for_n_cases": 0,
            "leaderboard_accessible_to_readers": True,
            "is_educational": False,
        },
    )

    assert not form.is_valid()
    assert form.errors["is_educational"] == [
        "Reader study must be educational when making leaderboard accessible to readers."
    ]

    form = ReaderStudyCreateForm(
        user=user,
        data={
            "roll_over_answers_for_n_cases": 0,
            "leaderboard_accessible_to_readers": True,
            "is_educational": True,
        },
    )

    assert not form.is_valid()
    assert "is_educational" not in form.errors.keys()


@pytest.mark.django_db
def test_validate_autosave_requires_answer_modification(client):
    user = UserFactory()
    form = ReaderStudyCreateForm(
        user=user,
        data={
            "roll_over_answers_for_n_cases": 0,
            "allow_answer_modification": False,
            "enable_autosaving": True,
        },
    )

    assert "enable_autosaving" in form.errors
    assert form.errors["enable_autosaving"] == [
        "Autosaving can only be enabled when also allowing answer modification."
    ]

    form = ReaderStudyCreateForm(
        user=user,
        data={
            "roll_over_answers_for_n_cases": 0,
            "allow_answer_modification": True,
            "enable_autosaving": True,
        },
    )

    assert "enable_autosaving" not in form.errors
