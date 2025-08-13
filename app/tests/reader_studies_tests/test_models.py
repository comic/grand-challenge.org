from contextlib import nullcontext
from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError

from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    Question,
    QuestionWidgetKindChoices,
    ReaderStudy,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.utilization_tests.factories import SessionUtilizationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_group_deletion():
    rs = ReaderStudyFactory()
    readers_group = rs.readers_group
    editors_group = rs.editors_group

    assert readers_group
    assert editors_group

    ReaderStudy.objects.filter(pk__in=[rs.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        readers_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["readers_group", "editors_group"])
def test_group_deletion_reverse(group):
    rs = ReaderStudyFactory()
    readers_group = rs.readers_group
    editors_group = rs.editors_group

    assert readers_group
    assert editors_group

    with pytest.raises(ProtectedError):
        getattr(rs, group).delete()


@pytest.mark.django_db
def test_read_only_fields():
    rs = ReaderStudyFactory()
    q = QuestionFactory(reader_study=rs)

    assert q.is_fully_editable is True
    assert q.read_only_fields == []

    AnswerFactory(question=q, answer="true")

    assert q.is_fully_editable is False
    assert q.read_only_fields == [
        "question_text",
        "answer_type",
        "image_port",
        "required",
        "overlay_segments",
        "widget",
        "answer_min_value",
        "answer_max_value",
        "answer_step_size",
        "answer_min_length",
        "answer_max_length",
        "answer_match_pattern",
        "interface",
    ]


@pytest.mark.django_db
def test_progress_for_user(settings):  # noqa: C901
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    im1, im2 = ImageFactory(name="im1"), ImageFactory(name="im2")
    q1, q2, q3 = [
        QuestionFactory(reader_study=rs),
        QuestionFactory(reader_study=rs),
        QuestionFactory(reader_study=rs),
    ]

    reader = UserFactory()
    rs.add_reader(reader)

    question_perc = 100 / 6

    assert rs.get_progress_for_user(reader) == {
        "diff": 0.0,
        "hangings": 0.0,
        "questions": 0.0,
    }

    ci = ComponentInterface.objects.get(slug="generic-medical-image")
    civ1 = ComponentInterfaceValueFactory(image=im1, interface=ci)
    civ2 = ComponentInterfaceValueFactory(image=im2, interface=ci)
    ds1, ds2 = DisplaySetFactory(reader_study=rs), DisplaySetFactory(
        reader_study=rs
    )
    ds1.values.add(civ1)
    ds2.values.add(civ2)

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == 0

    a11 = AnswerFactory(question=q1, answer="foo", creator=reader)
    a11.display_set = ds1
    a11.save()

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == pytest.approx(question_perc)

    a21 = AnswerFactory(question=q1, answer="foo", creator=reader)
    a21.display_set = ds2
    a21.save()

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == pytest.approx(question_perc * 2)

    a12 = AnswerFactory(question=q2, answer="foo", creator=reader)
    a13 = AnswerFactory(question=q3, answer="foo", creator=reader)
    a12.display_set = ds1
    a12.save()
    a13.display_set = ds1
    a13.save()

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 50
    assert progress["questions"] == pytest.approx(question_perc * 4)

    editor = UserFactory()
    rs.add_reader(editor)
    rs.add_editor(editor)

    for q in [q1, q2, q3]:
        for ds in [ds1, ds2]:
            AnswerFactory(
                question=q,
                answer="foo",
                creator=editor,
                is_ground_truth=True,
                display_set=ds,
            )

    progress = rs.get_progress_for_user(editor)
    assert progress["hangings"] == 0
    assert progress["questions"] == 0

    for q in [q1, q2, q3]:
        for ds in [ds1, ds2]:
            AnswerFactory(
                question=q,
                answer="foo",
                creator=editor,
                is_ground_truth=False,
                display_set=ds,
            )

    progress = rs.get_progress_for_user(editor)
    assert progress["hangings"] == 100.0
    assert progress["questions"] == 100.0


@pytest.mark.django_db
def test_leaderboard(  # noqa: C901
    reader_study_with_gt, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()
    e = rs.editors_group.user_set.first()

    with django_capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for ds in rs.display_sets.all():
                AnswerFactory(
                    question=question, creator=r1, answer=True, display_set=ds
                )

    leaderboard = rs.leaderboard
    assert Answer.objects.filter(is_ground_truth=False).count() == 6
    assert leaderboard["question_count"] == 6.0
    scores = leaderboard["grouped_scores"]
    assert len(scores) == 1
    user_score = scores[0]
    assert user_score["creator__username"] == r1.username
    assert user_score["score__sum"] == 6.0
    assert user_score["score__avg"] == 1.0

    with django_capture_on_commit_callbacks(execute=True):
        for i, question in enumerate(rs.questions.all()):
            for j, ds in enumerate(rs.display_sets.all()):
                AnswerFactory(
                    question=question,
                    creator=r2,
                    answer=(i + j) % 2 == 0,
                    display_set=ds,
                )

    del rs.scores_by_user
    del rs.leaderboard
    leaderboard = rs.leaderboard
    assert Answer.objects.filter(is_ground_truth=False).count() == 12
    assert leaderboard["question_count"] == 6.0
    scores = leaderboard["grouped_scores"]
    assert len(scores) == 2
    for user_score in scores:
        if user_score["creator__username"] != r2.username:
            continue
        assert user_score["score__sum"] == 3.0
        assert user_score["score__avg"] == 0.5

    with django_capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for ds in rs.display_sets.all():
                AnswerFactory(
                    question=question, creator=e, answer=True, display_set=ds
                )

    del rs.scores_by_user
    del rs.leaderboard
    leaderboard = rs.leaderboard
    assert Answer.objects.filter(is_ground_truth=False).count() == 18
    assert leaderboard["question_count"] == 6.0
    scores = leaderboard["grouped_scores"]
    assert len(scores) == 3
    for user_score in scores:
        if user_score["creator__username"] != e.username:
            continue
        assert user_score["score__sum"] == 6.0
        assert user_score["score__avg"] == 1.0


@pytest.mark.django_db
def test_statistics(
    reader_study_with_gt, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()

    rs_questions = rs.questions.values_list("question_text", flat=True)

    with django_capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for ds in rs.display_sets.all():
                AnswerFactory(
                    question=question, creator=r1, answer=True, display_set=ds
                )

    statistics = rs.statistics
    assert Answer.objects.filter(is_ground_truth=False).count() == 6
    assert statistics["max_score_questions"] == 2.0
    scores = statistics["scores_by_question"]
    assert len(scores) == rs.questions.count()
    questions = set(rs_questions)
    for score in scores:
        questions -= {score["question__question_text"]}
        assert score["score__sum"] == 2.0
        assert score["score__avg"] == 1.0
    assert questions == set()

    scores = statistics["scores_by_case"]
    assert len(scores) == rs.display_sets.count()
    ds = set(rs.display_sets.values_list("pk", flat=True))
    for score in scores:
        ds -= {score.id}
        assert score.sum == 3.0
        assert score.avg == 1.0
    assert ds == set()

    with django_capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for ds in rs.display_sets.all():
                answer = (
                    question.question_text == "q1"
                    and ds.values.first().image.name == "im1"
                )
                AnswerFactory(
                    question=question,
                    creator=r2,
                    answer=answer,
                    display_set=ds,
                )

    del rs.statistics
    statistics = rs.statistics
    assert Answer.objects.filter(is_ground_truth=False).count() == 12
    assert statistics["max_score_cases"] == 6.0
    scores = statistics["scores_by_question"]
    assert len(scores) == rs.questions.count()
    questions = set(rs_questions)
    for score in scores:
        questions -= {score["question__question_text"]}
        if score["question__question_text"] == "q1":
            assert score["score__sum"] == 3.0
            assert score["score__avg"] == 0.75
        else:
            assert score["score__sum"] == 2.0
            assert score["score__avg"] == 0.5
    assert questions == set()

    assert sorted(statistics["questions"]) == sorted(rs_questions)
    for ds in rs.display_sets.all():
        assert sorted(statistics["ground_truths"][ds.pk].keys()) == sorted(
            rs_questions
        )


@pytest.mark.django_db
def test_score_for_user(
    reader_study_with_gt, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1 = rs.readers_group.user_set.first()

    with django_capture_on_commit_callbacks(execute=True):
        for i, question in enumerate(rs.questions.all()):
            for j, ds in enumerate(rs.display_sets.all()):
                AnswerFactory(
                    question=question,
                    creator=r1,
                    answer=(i + j) % 2 == 0,
                    display_set=ds,
                )

    score = rs.score_for_user(r1)
    assert Answer.objects.filter(is_ground_truth=False).count() == 6
    assert score["score__sum"] == 3.0
    assert score["score__avg"] == 0.5


@pytest.mark.django_db
def test_help_markdown_is_scrubbed(client):
    rs = ReaderStudyFactory(
        help_text_markdown="<b>My Help Text</b><script>naughty</script>",
    )
    u = UserFactory()
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=rs.api_url, user=u)

    assert response.status_code == 200
    assert response.json()["help_text"] == "<p><b>My Help Text</b>naughty</p>"


@pytest.mark.django_db
def test_description_is_scrubbed(client):
    u = UserFactory()
    im, im1 = ImageFactory(), ImageFactory()
    rs = ReaderStudyFactory(
        case_text={
            im.name: "<b>My Help Text</b><script>naughty</script>",
            "not an image name": "Shouldn't appear in result",
            im1.name: "Doesn't belong to this study so ignore",
        },
    )
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(ComponentInterfaceValueFactory(image=im))
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=ds.api_url, user=u)

    assert response.status_code == 200
    # Case should be indexed with the api url
    assert (
        response.json()["description"] == "<p><b>My Help Text</b>naughty</p>"
    )


@pytest.mark.django_db
def test_description_not_repeated(client):
    u = UserFactory()
    im = ImageFactory()
    rs = ReaderStudyFactory(
        case_text={
            im.name: "One line of text",
        },
    )
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(ComponentInterfaceValueFactory(image=im))
    ds.values.add(ComponentInterfaceValueFactory(image=im))
    ds.values.add(ComponentInterfaceValueFactory(image=im))
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=ds.api_url, user=u)

    assert response.status_code == 200
    # Case should be indexed with the api url
    assert response.json()["description"] == "<p>One line of text</p>"


@pytest.mark.django_db
def test_validate_answer():
    u = UserFactory()
    rs = ReaderStudyFactory()

    rs.add_reader(u)
    ds = DisplaySetFactory(reader_study=rs)
    q = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOOL,
        question_text="q1",
    )

    AnswerFactory(creator=u, question=q, answer=True, display_set=ds)

    with pytest.raises(ValidationError) as e:
        Answer.validate(creator=u, question=q, answer=True, display_set=ds)

    assert (
        e.value.message
        == f"User {u} has already answered this question for this display set."
    )

    ds = DisplaySetFactory(reader_study=rs)
    assert (
        Answer.validate(creator=u, question=q, answer=True, display_set=ds)
        is None
    )


NUMBER_ANSWER_VALIDATION_INPUT = (
    (
        AnswerType.NUMBER,
        None,
        {
            "required": False,
        },
        nullcontext(),
    ),
    (
        AnswerType.NUMBER,
        None,
        {
            "required": True,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.NUMBER,
        2,
        {
            "answer_min_value": 0,
            "answer_max_value": 5,
            "answer_step_size": 0.5,
        },
        nullcontext(),
    ),
    (
        AnswerType.NUMBER,
        6,
        {
            "answer_min_value": 0,
            "answer_max_value": 5,
            "answer_step_size": 0.5,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.NUMBER,
        4.7,
        {
            "answer_min_value": 0,
            "answer_max_value": 5,
            "answer_step_size": 0.5,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.NUMBER,
        -1,
        {
            "answer_min_value": 0,
            "answer_max_value": 5,
            "answer_step_size": 0.5,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.NUMBER,
        0,
        {
            "answer_min_value": 0,
            "answer_max_value": 5,
            "answer_step_size": 0.5,
        },
        nullcontext(),
    ),
    (
        AnswerType.NUMBER,
        1.1,
        {
            "answer_min_value": 0.1,
            "answer_step_size": 1,
        },
        nullcontext(),
    ),
    (
        AnswerType.NUMBER,
        1.1,
        {
            "answer_max_value": 2.1,
            "answer_step_size": 1,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.NUMBER,
        1.9,
        {
            "answer_min_value": -0.1,
            "answer_step_size": 2.0,
        },
        nullcontext(),
    ),
)

TEXT_ANSWER_VALIDATION_INPUT = (
    (
        AnswerType.TEXT,
        "",
        {
            "required": False,
        },
        nullcontext(),
    ),
    (
        AnswerType.TEXT,
        "",
        {
            "required": True,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.TEXT,
        "",
        {
            "answer_min_length": 1,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.TEXT,
        "1234",
        {
            "answer_min_length": 4,
        },
        nullcontext(),
    ),
    (
        AnswerType.TEXT,
        "12",
        {
            "answer_max_length": 2,
        },
        nullcontext(),
    ),
    (
        AnswerType.TEXT,
        "1234",
        {
            "answer_max_length": 2,
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.TEXT,
        "123",
        {
            "answer_min_length": 3,
            "answer_max_length": 3,
        },
        nullcontext(),
    ),
    (
        AnswerType.TEXT,
        "hello world",
        {
            "answer_match_pattern": r"^hello world$",
        },
        nullcontext(),
    ),
    (
        AnswerType.TEXT,
        "not hello world",
        {
            "answer_match_pattern": r"^hello world$",
        },
        pytest.raises(ValidationError),
    ),
    (
        AnswerType.TEXT,
        "",
        {
            "answer_min_size": 1,
            "required": False,
        },
        nullcontext(),
    ),
)


@pytest.mark.parametrize(
    "answer_type, answer, extra_params, error",
    (*NUMBER_ANSWER_VALIDATION_INPUT, *TEXT_ANSWER_VALIDATION_INPUT),
)
@pytest.mark.django_db
def test_validate_answer_input_settings(
    answer_type, answer, extra_params, error
):
    u = UserFactory()
    rs = ReaderStudyFactory()

    rs.add_reader(u)
    ds = DisplaySetFactory(reader_study=rs)
    qu = QuestionFactory(
        reader_study=rs,
        answer_type=answer_type,
        question_text="q1",
    )
    if extra_params:
        for param, value in extra_params.items():
            setattr(qu, param, value)

    with error:
        Answer.validate(creator=u, question=qu, answer=answer, display_set=ds)


@pytest.mark.django_db
def test_display_set_order():
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    assert ds.order == 10

    ds = DisplaySetFactory(reader_study=rs)
    assert ds.order == 20

    ds.order = 15
    ds.save()

    ds = DisplaySetFactory(reader_study=rs)
    assert ds.order == 20


@pytest.mark.django_db
def test_display_set_description():
    rs = ReaderStudyFactory()
    reader = UserFactory()
    rs.add_reader(reader)
    images = [ImageFactory() for _ in range(6)]
    ci = ComponentInterface.objects.get(slug="generic-medical-image")
    result = {}
    for image in images:
        ds = DisplaySetFactory(reader_study=rs)
        result[ds.pk] = f"<p>{str(image.pk)}</p>"
        civ = ComponentInterfaceValueFactory(interface=ci, image=image)
        ds.values.add(civ)

    rs.case_text = {im.name: str(im.pk) for im in images}
    rs.case_text["no_image"] = "not an image"
    rs.save()

    for ds in rs.display_sets.all():
        assert ds.description == result[ds.pk]


@pytest.fixture(scope="function")
def display_set_with_title(db):
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)

    # Default
    assert ds.title == ""

    # Update
    ds.title = "A Display Set Title"
    ds.save()

    return ds


@pytest.mark.django_db
def test_display_set_duplicate_title_edit(display_set_with_title):
    # Sanity
    ds = DisplaySetFactory(
        reader_study=display_set_with_title.reader_study,
        title="Another Display Set",
    )

    ds.title = display_set_with_title.title
    with pytest.raises(IntegrityError):
        ds.save()


@pytest.mark.django_db
def test_display_set_duplicate_title_create(display_set_with_title):
    with pytest.raises(IntegrityError):
        DisplaySetFactory(
            reader_study=display_set_with_title.reader_study,
            title=display_set_with_title.title,
        )


@pytest.mark.django_db
def test_display_set_duplicate_title_other_reader_study(
    display_set_with_title,
):
    # Another reader study is not problem
    DisplaySetFactory(
        reader_study=ReaderStudyFactory(),
        title=display_set_with_title.title,
    )


@pytest.mark.django_db
def test_question_interface():
    q = QuestionFactory(
        answer_type=AnswerType.TEXT,
        widget=QuestionWidgetKindChoices.TEXT_INPUT,
    )
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    q.interface = ci_str
    q.clean()
    q.save()
    q.refresh_from_db()

    assert q.interface == ci_str

    ci_img = ComponentInterface.objects.filter(
        kind=InterfaceKindChoices.IMAGE
    ).first()
    q.interface = ci_img

    with pytest.raises(ValidationError) as e:
        q.clean()

    assert e.value.message == (
        f"The socket {ci_img} is not allowed for this "
        f"question type ({AnswerType.TEXT})"
    )

    q.refresh_from_db()

    assert q.interface == ci_str


@pytest.mark.django_db
def test_workstation_url():
    workstation = WorkstationFactory()
    reader_study = ReaderStudyFactory(workstation=workstation)
    display_set = DisplaySetFactory(reader_study=reader_study)

    assert (
        display_set.workstation_url
        == f"https://testserver/viewers/{workstation.slug}/sessions/create/display-set/{display_set.pk}?"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, widget, interface, error",
    (
        (
            AnswerType.MULTIPLE_POINTS,
            "",
            False,
            nullcontext(),
        ),
        (
            AnswerType.POINT,
            QuestionWidgetKindChoices.ACCEPT_REJECT,
            True,
            pytest.raises(ValidationError),
        ),
        (
            AnswerType.MULTIPLE_POINTS,
            QuestionWidgetKindChoices.ACCEPT_REJECT,
            False,
            pytest.raises(ValidationError),
        ),
        (
            AnswerType.MULTIPLE_POINTS,
            QuestionWidgetKindChoices.ACCEPT_REJECT,
            True,
            nullcontext(),
        ),
        (
            AnswerType.TEXT,  # Requires a widget choice
            "",
            False,
            pytest.raises(ValidationError),
        ),
    ),
)
def test_clean_question_widget(answer_type, widget, interface, error):
    if interface:
        kind = [
            member
            for name, member in ComponentInterface.Kind.__members__.items()
            if name == answer_type.name
        ]
        ci = ComponentInterfaceFactory(kind=kind[0])
    else:
        ci = None

    q = QuestionFactory(
        question_text="foo",
        answer_type=answer_type,
        widget=widget,
        interface=ci,
    )

    with error:
        q._clean_widget()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, widget, options, error, error_message",
    (
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": 1},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_max_value": 5},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": -1},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": 0},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.ACCEPT_REJECT,
            {"answer_min_value": 1},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input or Number Range widgets for answers of type Number.",
        ),
        (
            AnswerType.NUMBER,
            "",
            {"answer_min_value": 1},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input or Number Range widgets for answers of type Number.",
        ),
        (
            AnswerType.NUMBER,
            "",
            {"answer_step_size": 0},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input or Number Range widgets for answers of type Number.",
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_step_size": 0.5},
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {
                "answer_step_size": 0.5,
                "answer_min_value": 0,
                "answer_max_value": 4,
            },
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {
                "answer_min_value": 4,
                "answer_max_value": 0,
            },
            pytest.raises(ValidationError),
            "Answer max value needs to be bigger than answer min value.",
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {
                "answer_min_value": 0,
                "answer_max_value": 0,
            },
            pytest.raises(ValidationError),
            "Answer max value needs to be bigger than answer min value.",
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_RANGE,
            {},
            pytest.raises(ValidationError),
            "Number Range widget requires answer min, max and step values to be set.",
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_RANGE,
            {
                "answer_step_size": 0.5,
                "answer_min_value": 0,
                "answer_max_value": 4,
            },
            nullcontext(),
            None,
        ),
        (
            AnswerType.NUMBER,
            QuestionWidgetKindChoices.NUMBER_RANGE,
            {
                "answer_min_value": 0,
                "answer_max_value": 0,
                "answer_step_size": 1,
            },
            pytest.raises(ValidationError),
            "Answer max value needs to be bigger than answer min value.",
        ),
        *(
            (
                AnswerType.BOOL,
                widget,
                {"answer_min_length": 1},
                pytest.raises(ValidationError),
                "Minimum length, maximum length, and/or pattern match for answers "
                "can only be defined for the answers of type Text.",
            )
            for widget in (
                "",
                QuestionWidgetKindChoices.TEXT_INPUT,
                QuestionWidgetKindChoices.TEXT_AREA,
            )
        ),
    ),
)
def test_clean_widget_options(
    answer_type, widget, options, error, error_message
):
    qu = QuestionFactory(
        question_text="foo",
        answer_type=answer_type,
        widget=widget,
    )
    if options:
        for option, value in options.items():
            setattr(qu, option, value)

    with error as e:
        qu._clean_widget_options()

    if error_message:
        assert e.value.message == error_message


@pytest.mark.django_db
def test_annotation_view_port_contains_image():
    image_interface = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.IMAGE
    )
    mp4_interface = ComponentInterfaceFactory(kind=InterfaceKindChoices.MP4)

    reader_study = ReaderStudyFactory(
        view_content={
            "main": [image_interface.slug],
            "secondary": [mp4_interface.slug],
        }
    )
    reader_study.full_clean()

    question = Question(
        reader_study=reader_study,
        question_text="foo",
        answer_type=AnswerType.MASK,
        image_port=Question.ImagePort.MAIN,
    )
    question.full_clean()
    question.save()

    question = Question(
        reader_study=reader_study,
        question_text="foo",
        answer_type=AnswerType.MASK,
        image_port=Question.ImagePort.SECONDARY,
    )

    with pytest.raises(ValidationError) as err:
        question.full_clean()

    assert (
        "The Secondary view port does not contain an image. "
        "Please update the view content of this reader study or select a different view port for question foo"
        in str(err.value)
    )

    question = Question(
        reader_study=reader_study,
        question_text="foo",
        answer_type=AnswerType.MASK,
        image_port=Question.ImagePort.TERTIARY,
    )

    with pytest.raises(ValidationError) as err:
        question.full_clean()

    assert (
        "The Tertiary view port has not been defined. "
        "Please update the view content of this reader study or select a different view port for question foo"
        in str(err.value)
    )

    reader_study.view_content = {"secondary": [mp4_interface.slug]}

    with pytest.raises(ValidationError) as err:
        reader_study.full_clean()

    assert (
        "The Main view port has not been defined. "
        "Please update the view content of this reader study or select a different view port for question foo"
        in str(err.value)
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, required, error, error_message",
    (
        (
            AnswerType.NUMBER,
            False,
            nullcontext(),
            None,
        ),
        (
            AnswerType.HEADING,
            False,
            pytest.raises(ValidationError),
            "Empty answer confirmation is not supported for Heading type questions.",
        ),
        (
            AnswerType.CHOICE,
            False,
            pytest.raises(ValidationError),
            "Empty answer confirmation is not supported for Choice type questions.",
        ),
        (
            AnswerType.MULTIPLE_CHOICE,
            False,
            pytest.raises(ValidationError),
            "Empty answer confirmation is not supported for Multiple choice type questions.",
        ),
        (
            AnswerType.NUMBER,
            True,
            pytest.raises(ValidationError),
            "Cannot have answer confirmation and have a question be "
            "required at the same time",
        ),
    ),
)
def test_empty_answer_confirmation_validation(
    answer_type, required, error, error_message
):
    qu = QuestionFactory(
        empty_answer_confirmation=True,
        answer_type=answer_type,
        required=required,
        question_text="foo",
    )

    with error as e:
        qu._clean_empty_answer_confirmation()

    if error_message:
        assert error_message in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type, interactive_algorithm, error",
    (
        (
            AnswerType.MASK,
            InteractiveAlgorithmChoices.ULS23_BASELINE,
            nullcontext(),
        ),
        *[
            (answer_type, "", nullcontext())
            for answer_type in AnswerType.values
        ],
        *[
            (
                answer_type,
                InteractiveAlgorithmChoices.ULS23_BASELINE,
                pytest.raises(ValidationError),
            )
            for answer_type in AnswerType.values
            if answer_type != AnswerType.MASK
        ],
    ),
)
def test_clean_question_interactive_algorithms(
    answer_type, interactive_algorithm, error
):
    q = QuestionFactory(
        question_text="foo",
        answer_type=answer_type,
        interactive_algorithm=interactive_algorithm,
    )

    with error:
        q._clean_interactive_algorithm()


@pytest.mark.django_db
def test_ground_truth_complete():
    rs = ReaderStudyFactory()

    ds1, ds2 = DisplaySetFactory.create_batch(2, reader_study=rs)
    q1, q2 = QuestionFactory.create_batch(
        2,
        reader_study=rs,
        answer_type=AnswerType.TEXT,  # Answerable and Ground Truth applicable
    )

    # Sanity
    assert not rs.ground_truth_is_complete

    # Add two questions that are not ground truth applicable
    QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.HEADING,
    )
    QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOUNDING_BOX_2D,
    )

    # Creating ground truth answers: note missing the second display set, second question answer
    AnswerFactory(display_set=ds1, question=q1, is_ground_truth=True)
    AnswerFactory(display_set=ds1, question=q2, is_ground_truth=True)
    AnswerFactory(display_set=ds2, question=q1, is_ground_truth=True)

    # Sanity, add a technically allowed duplicate GT answer
    AnswerFactory(display_set=ds1, question=q1, is_ground_truth=True)
    assert (
        not rs.ground_truth_is_complete
    ), "One GT answer should (still) be missing"

    AnswerFactory(display_set=ds2, question=q2, is_ground_truth=False)
    assert not rs.ground_truth_is_complete, "Non GT answer does not count"

    AnswerFactory(display_set=ds2, question=q2, is_ground_truth=True)
    assert rs.ground_truth_is_complete, "All GT answers are given"


@pytest.mark.django_db
def test_answer_score_calculation():
    rs = ReaderStudyFactory()

    ds = DisplaySetFactory(reader_study=rs)
    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    reader = UserFactory()
    rs.add_reader(reader)

    # Ground truth
    gt = AnswerFactory(
        question=q,
        creator=reader,
        answer=True,
        display_set=ds,
        is_ground_truth=True,
    )

    assert gt.score is None, "Ground truth does not get a score"

    answer = AnswerFactory(
        question=q,
        creator=reader,
        answer=True,
        display_set=ds,
    )

    assert answer.score == 1.0, "Creating an answer calculates a score"

    answer.answer = False
    answer.save()

    answer.refresh_from_db()  # Sanity
    assert answer.score == 0.0, "Updating an answer re-calculates a score"


@pytest.mark.django_db
def test_reader_study_not_launchable_when_max_credits_consumed():
    reader_study = ReaderStudyFactory(max_credits=100)

    assert reader_study.is_launchable

    session_utilization = SessionUtilizationFactory(
        duration=timedelta(hours=1)
    )
    session_utilization.reader_studies.add(reader_study)

    assert reader_study.session_utilizations.count() == 1
    assert reader_study.session_utilizations.first().credits_consumed == 500
    assert reader_study.credits_consumed == 500
    assert not reader_study.is_launchable


def test_all_question_fields_defined_in_copy_or_non_copy():
    assert {
        f.name for f in Question._meta.get_fields()
    } == Question.copy_fields | Question._non_copy_fields
