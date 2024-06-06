import csv
import html
import io

import pytest
from actstream.actions import is_following
from django.contrib.auth.models import Permission
from django.db.models import BLANK_CHOICE_DASH
from guardian.shortcuts import assign_perm

from grandchallenge.cases.widgets import FlexibleImageWidget
from grandchallenge.components.forms import SingleCIVForm
from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.components.widgets import SelectUploadWidget
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.reader_studies.forms import (
    DisplaySetCreateForm,
    DisplaySetUpdateForm,
    QuestionForm,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    Question,
    QuestionWidgetKindChoices,
    ReaderStudy,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstation_configs.models import LookUpTable
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import (
    ImageFactory,
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.reader_studies_tests import RESOURCE_PATH
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies, get_rs_creator
from tests.uploads_tests.factories import UserUploadFactory
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
        kind=InterfaceKindChoices.SEGMENTATION,
        overlay_segments=[
            {"name": "s1", "visible": True, "voxel_value": 0},
            {"name": "s2", "visible": True, "voxel_value": 1},
        ],
    )
    form = QuestionForm(
        reader_study=question.reader_study,
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
        (AnswerType.MASK, InterfaceKindChoices.SEGMENTATION),
        (AnswerType.ELLIPSE, InterfaceKindChoices.ELLIPSE),
        (AnswerType.MULTIPLE_ELLIPSES, InterfaceKindChoices.MULTIPLE_ELLIPSES),
    ),
)
def test_question_form_interface_field(answer_type, interface_kind):
    ci = ComponentInterfaceFactory(kind=interface_kind)
    ci_img = ComponentInterface.objects.filter(
        kind=InterfaceKindChoices.IMAGE
    ).first()
    assert ci_img is not None
    form = QuestionForm(
        reader_study=ReaderStudyFactory(), initial={"answer_type": answer_type}
    )
    assert form.interface_choices().filter(pk=ci.pk).exists()
    assert not form.interface_choices().filter(pk=ci_img.pk).exists()


@pytest.mark.django_db
def test_question_form_interface_field_no_answer_type():
    assert ComponentInterface.objects.count() > 0
    form = QuestionForm(
        reader_study=ReaderStudyFactory(), initial={"answer_type": None}
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
def test_reader_study_copy(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory(title="copied")
    editor = UserFactory()
    editor2 = UserFactory()
    reader = UserFactory()
    rs.add_reader(reader)
    rs.add_editor(editor)
    rs.add_editor(editor2)
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
    )
    CategoricalOptionFactory(question=question, title="option1")
    QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOOL,
        question_text="q2",
        order=4664,
    )

    im1, im2 = ImageFactory(), ImageFactory()
    interfaces = []
    for index, im in enumerate([im1, im2]):
        civ = ComponentInterfaceValueFactory(image=im)
        interfaces.append(civ.interface.slug)
        count = index + 1
        ds = DisplaySetFactory(
            reader_study=rs,
            title=f"display set title {count}",
            order=count,
        )
        ds.values.add(civ)
    rs.view_content = {"main": interfaces[0], "secondary": interfaces[1]}
    rs.hanging_protocol = HangingProtocolFactory()
    rs.case_text = {im1.name: "test", im2.name: "test2"}
    rs.workstation_config = WorkstationConfigFactory()
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
    assert _rs.display_sets.count() == 0
    assert _rs.questions.count() == 0
    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1
    assert _rs.case_text == {}
    assert _rs.workstation_config == rs.workstation_config

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
    assert _rs.display_sets.count() == 0
    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    question.refresh_from_db()
    copied_question = _rs.questions.first()

    assert question.reader_study == rs
    assert copied_question.pk != question.pk
    assert copied_question.reader_study != question.reader_study

    # check that all but the specified fields have been copied over
    non_copied_fields = [
        "questionuserobjectpermission",
        "questiongroupobjectpermission",
        "answer",
        "reader_study",
        "id",
        "created",
        "modified",
        "options",
    ]
    for field in copied_question._meta.get_fields():
        if field.name not in non_copied_fields:
            assert getattr(copied_question, field.name) == getattr(
                question, field.name
            )

    assert copied_question.options.get().title == question.options.get().title
    assert copied_question.options.get().pk != question.options.get().pk

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:copy",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={"title": "3", "copy_display_sets": True},
            user=editor,
            follow=True,
        )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 4

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "3"
    assert _rs.questions.count() == 0

    assert _rs.display_sets.count() == 2
    _ds = _rs.display_sets.first()
    assert _ds.title == "display set title 1"
    assert _ds.order == 1

    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:copy",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={
                "title": "4",
                "copy_display_sets": True,
                "copy_view_content": True,
                "copy_hanging_protocol": True,
            },
            user=editor,
            follow=True,
        )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 5

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "4"
    assert _rs.questions.count() == 0
    assert _rs.display_sets.count() == 2
    assert _rs.view_content == rs.view_content
    assert _rs.hanging_protocol == rs.hanging_protocol
    assert _rs.case_text == {}
    assert _rs.readers_group.user_set.count() == 0
    assert _rs.editors_group.user_set.count() == 1

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="reader-studies:copy",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": rs.slug},
            data={
                "title": "5",
                "copy_display_sets": True,
                "copy_case_text": True,
            },
            user=editor,
            follow=True,
        )

    assert response.status_code == 200
    assert ReaderStudy.objects.count() == 6

    _rs = ReaderStudy.objects.order_by("created").last()
    assert _rs.title == "5"
    assert _rs.questions.count() == 0
    assert _rs.display_sets.count() == 2
    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
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
    assert _rs.display_sets.count() == 0
    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
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
    assert _rs.display_sets.count() == 0
    assert _rs.view_content == {}
    assert _rs.hanging_protocol is None
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
        viewname="reader-studies:add-ground-truth",
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
    "form_class, file_widget",
    (
        (DisplaySetCreateForm, UserUploadSingleWidget),
        (DisplaySetUpdateForm, SelectUploadWidget),
    ),
)
def test_display_set_update_form(form_class, file_widget):
    rs = ReaderStudyFactory()
    user = UserFactory()
    rs.add_editor(user)
    ds = DisplaySetFactory(reader_study=rs)
    for slug, store_in_db in [("slug-1", False), ("slug-2", True)]:
        ci = ComponentInterfaceFactory(
            title=slug, kind="JSON", store_in_database=store_in_db
        )
        civ = ComponentInterfaceValueFactory(interface=ci)
        ds.values.add(civ)

    instance = None if form_class == DisplaySetCreateForm else ds
    form = form_class(user=user, instance=instance, base_obj=rs)
    assert sorted(form.fields.keys()) == ["order", "slug-1", "slug-2", "title"]
    assert isinstance(form.fields["slug-1"].widget, file_widget)
    assert isinstance(form.fields["slug-2"].widget, JSONEditorWidget)

    ci = ComponentInterfaceFactory(kind="STR", title="slug-3")
    QuestionFactory(reader_study=rs, answer_type=AnswerType.TEXT, interface=ci)
    del rs.interfaces_and_values
    del rs.values_for_interfaces
    form = form_class(user=user, instance=instance, base_obj=rs)
    assert sorted(form.fields.keys()) == [
        "order",
        "slug-1",
        "slug-2",
        "slug-3",
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
    ci_img = ComponentInterfaceFactory(kind="IMG")
    ci_file = ComponentInterfaceFactory(kind="JSON", store_in_database=False)
    ci_str = ComponentInterfaceFactory(kind="STR")
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
        kind=InterfaceKind.InterfaceKindChoices.IMAGE, title="image"
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
    assert im1 in form.fields["image"].fields[0].queryset.all()
    assert im2 not in form.fields["image"].fields[0].queryset.all()
    assert upload1 in form.fields["image"].fields[1].queryset.all()
    assert upload2 not in form.fields["image"].fields[1].queryset.all()


@pytest.mark.django_db
def test_display_set_add_interface_form():
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    user = UserFactory()
    rs.add_editor(user)

    ci_file = ComponentInterfaceFactory(kind="JSON", store_in_database=False)
    ci_value = ComponentInterfaceFactory(kind="JSON", store_in_database=True)
    ci_image = ComponentInterfaceFactory(kind="IMG", store_in_database=False)

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
    assert sorted(form.fields.keys()) == [ci_file.slug, "interface"]
    assert isinstance(form.fields[ci_file.slug].widget, UserUploadSingleWidget)

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=ci_value.pk,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == [ci_value.slug, "interface"]
    assert isinstance(form.fields[ci_value.slug].widget, JSONEditorWidget)

    form = SingleCIVForm(
        pk=ds.pk,
        base_obj=rs,
        interface=ci_image.pk,
        user=user,
        htmx_url="foo",
        auto_id="1",
    )
    assert sorted(form.fields.keys()) == [ci_image.slug, "interface"]
    assert isinstance(form.fields[ci_image.slug].widget, FlexibleImageWidget)


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
        initial=(
            {"answer_type": answer_type} if answer_type is not None else {}
        ),
    )
    assert form.widget_choices() == choices


@pytest.mark.django_db
def test_question_form_initial_widget():
    qu = QuestionFactory(answer_type=AnswerType.TEXT)
    form = QuestionForm(reader_study=ReaderStudyFactory(), instance=qu)
    assert not form.initial_widget()

    qu.widget = QuestionWidgetKindChoices.ACCEPT_REJECT
    form2 = QuestionForm(reader_study=ReaderStudyFactory(), instance=qu)
    assert form2.initial_widget() == QuestionWidgetKindChoices.ACCEPT_REJECT


@pytest.mark.django_db
def test_question_widget_choices_for_non_editable_instance():
    # no matter whether the question is editable, widget choices should be the same
    qu = QuestionFactory(answer_type=AnswerType.TEXT)
    form = QuestionForm(reader_study=ReaderStudyFactory(), instance=qu)
    assert form.widget_choices() == [
        ("TEXT_INPUT", "Text Input"),
        ("TEXT_AREA", "Text Area"),
    ]
    AnswerFactory(question=qu, answer="Foo")
    form = QuestionForm(reader_study=ReaderStudyFactory(), instance=qu)
    assert form.widget_choices() == [
        ("TEXT_INPUT", "Text Input"),
        ("TEXT_AREA", "Text Area"),
    ]


@pytest.mark.django_db
def test_question_default_annotation_color():
    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
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
        data={
            "answer_type": AnswerType.MASK,
            "image_port": Question.ImagePort.MAIN,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
            "default_annotation_color": "#000000",
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
            "default_annotation_color": "",
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
            "default_annotation_color": None,
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        data={
            "answer_type": AnswerType.TEXT,
            "widget": QuestionWidgetKindChoices.TEXT_AREA,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
        },
    )
    assert form.is_valid()

    form = QuestionForm(
        reader_study=ReaderStudyFactory(),
        data={
            "answer_type": AnswerType.MASK,
            "image_port": Question.ImagePort.MAIN,
            "direction": Question.Direction.HORIZONTAL,
            "order": 100,
            "question_text": "gfda",
            "default_annotation_color": "#000",
        },
    )
    assert form.is_valid() is False
    assert form.errors == {
        "default_annotation_color": [
            "This is an invalid color code. It must be an HTML hexadecimal color code e.g. #000000"
        ]
    }
