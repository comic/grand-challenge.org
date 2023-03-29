from contextlib import nullcontext

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
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
def test_leaderboard(reader_study_with_gt, settings):  # noqa: C901
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()
    e = rs.editors_group.user_set.first()

    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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
def test_statistics(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()

    rs_questions = rs.questions.values_list("question_text", flat=True)

    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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
def test_score_for_user(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1 = rs.readers_group.user_set.first()

    with capture_on_commit_callbacks(execute=True):
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


@pytest.mark.parametrize(
    "answer_type, answer, extra_params, error",
    (
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
    ),
)
@pytest.mark.django_db
def test_validate_answer_number_input_settings(
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


@pytest.mark.django_db
def test_question_interface():
    q = QuestionFactory(answer_type=AnswerType.SINGLE_LINE_TEXT)
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
        q.save()

    assert e.value.message == (
        f"The interface {ci_img} is not allowed for this "
        f"question type ({AnswerType.SINGLE_LINE_TEXT})"
    )
    q.refresh_from_db()
    assert q.interface == ci_str


@pytest.mark.django_db
def test_main_image_from_ds():
    ds = DisplaySetFactory()
    ci1, ci2 = ComponentInterfaceFactory.create_batch(
        2, kind=InterfaceKindChoices.IMAGE
    )
    im1, im2 = ImageFactory.create_batch(2)
    ds.values.add(ComponentInterfaceValueFactory(interface=ci1, image=im1))
    ds.values.add(ComponentInterfaceValueFactory(interface=ci2, image=im2))

    # without view content set, the first image title is returned
    assert im1.name == ds.main_image_title

    # with a view content set, the first image title of the main viewport is returned
    ds.reader_study.view_content = {"main": [ci2.slug]}
    ds.reader_study.save()
    del ds.main_image_title
    assert im2.name == ds.main_image_title

    # if the ds does not have a civ for the interface specified in the view content, the first image title is returned
    ci3 = ComponentInterfaceFactory(kind=InterfaceKindChoices.IMAGE)
    ds.reader_study.view_content = {"main": [ci3.slug]}
    ds.reader_study.save()
    ds.refresh_from_db()
    del ds.main_image_title
    assert im1.name == ds.main_image_title


@pytest.mark.django_db
def test_workstation_url():
    workstation = WorkstationFactory()
    reader_study = ReaderStudyFactory(workstation=workstation)
    display_set = DisplaySetFactory(reader_study=reader_study)

    assert (
        display_set.workstation_url
        == f"https://testserver/viewers/{workstation.slug}/sessions/create/?displaySet={display_set.pk}"
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
    "widget, options, error, error_message",
    (
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {},
            nullcontext(),
            None,
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": 1},
            nullcontext(),
            None,
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_max_value": 5},
            nullcontext(),
            None,
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": -1},
            nullcontext(),
            None,
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_min_value": 0},
            nullcontext(),
            None,
        ),
        (
            QuestionWidgetKindChoices.ACCEPT_REJECT,
            {"answer_min_value": 1},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input widget for answers of type Number.",
        ),
        (
            "",
            {"answer_min_value": 1},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input widget for answers of type Number.",
        ),
        (
            "",
            {"answer_min_value": 0},
            pytest.raises(ValidationError),
            "Min and max values and the step size for answers "
            "can only be defined in combination with the "
            "Number Input widget for answers of type Number.",
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {"answer_step_size": 0.5},
            nullcontext(),
            None,
        ),
        (
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
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {
                "answer_min_value": 4,
                "answer_max_value": 0,
            },
            pytest.raises(ValidationError),
            "Answer max value needs to be bigger than answer min value.",
        ),
        (
            QuestionWidgetKindChoices.NUMBER_INPUT,
            {
                "answer_min_value": 0,
                "answer_max_value": 0,
            },
            pytest.raises(ValidationError),
            "Answer max value needs to be bigger than answer min value.",
        ),
    ),
)
def test_clean_widget_options(widget, options, error, error_message):
    qu = QuestionFactory(
        question_text="foo",
        widget=widget,
    )
    if options:
        for option, value in options.items():
            setattr(qu, option, value)

    with error as e:
        qu._clean_widget_options()

    if error_message:
        assert e.value.message == error_message
