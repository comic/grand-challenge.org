import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
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
    ]


@pytest.mark.django_db
def test_generate_hanging_list():
    rs = ReaderStudyFactory()
    im1 = ImageFactory(name="im1")
    im2 = ImageFactory(name="im2")

    rs.generate_hanging_list()
    assert rs.hanging_list == []

    rs.images.set([im1, im2])
    rs.generate_hanging_list()
    assert rs.hanging_list == [
        {"main": "im1"},
        {"main": "im2"},
    ]


@pytest.mark.django_db
def test_progress_for_user(settings):
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

    rs.images.set([im1, im2])
    rs.hanging_list = [{"main": im1.name}, {"main": im2.name}]
    rs.save()

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == 0

    a11 = AnswerFactory(question=q1, answer="foo", creator=reader)
    a11.images.add(im1)

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == pytest.approx(question_perc)

    a21 = AnswerFactory(question=q1, answer="foo", creator=reader)
    a21.images.add(im2)

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 0
    assert progress["questions"] == pytest.approx(question_perc * 2)

    a12 = AnswerFactory(question=q2, answer="foo", creator=reader)
    a12.images.add(im1)
    a13 = AnswerFactory(question=q3, answer="foo", creator=reader)
    a13.images.add(im1)

    progress = rs.get_progress_for_user(reader)
    assert progress["hangings"] == 50
    assert progress["questions"] == pytest.approx(question_perc * 4)

    editor = UserFactory()
    rs.add_reader(editor)
    rs.add_editor(editor)

    for q in [q1, q2, q3]:
        for im in [im1, im2]:
            a = AnswerFactory(
                question=q, answer="foo", creator=editor, is_ground_truth=True
            )
            a.images.add(im)

    progress = rs.get_progress_for_user(editor)
    assert progress["hangings"] == 0
    assert progress["questions"] == 0

    for q in [q1, q2, q3]:
        for im in [im1, im2]:
            a = AnswerFactory(
                question=q, answer="foo", creator=editor, is_ground_truth=False
            )
            a.images.add(im)

    progress = rs.get_progress_for_user(editor)
    assert progress["hangings"] == 100.0
    assert progress["questions"] == 100.0


@pytest.mark.django_db  # noqa: C901
def test_leaderboard(reader_study_with_gt, settings):  # noqa: C901
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()
    e = rs.editors_group.user_set.first()

    with capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for im in rs.images.all():
                ans = AnswerFactory(question=question, creator=r1, answer=True)
                ans.images.add(im)

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
            for j, im in enumerate(rs.images.all()):
                ans = AnswerFactory(
                    question=question, creator=r2, answer=(i + j) % 2 == 0
                )
                ans.images.add(im)

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
            for im in rs.images.all():
                ans = AnswerFactory(question=question, creator=e, answer=True)
                ans.images.add(im)

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


@pytest.mark.django_db  # noqa - C901
def test_statistics(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()

    rs_questions = rs.questions.values_list("question_text", flat=True)

    with capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for im in rs.images.all():
                ans = AnswerFactory(question=question, creator=r1, answer=True)
                ans.images.add(im)

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
    assert len(scores) == rs.images.count()
    images = set(rs.images.values_list("name", flat=True))
    for score in scores:
        images -= {score["images__name"]}
        assert score["score__sum"] == 3.0
        assert score["score__avg"] == 1.0
    assert images == set()

    with capture_on_commit_callbacks(execute=True):
        for question in rs.questions.all():
            for im in rs.images.all():
                answer = question.question_text == "q1" and im.name == "im1"
                ans = AnswerFactory(
                    question=question, creator=r2, answer=answer
                )
                ans.images.add(im)

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
    for im in rs.images.all():
        assert sorted(statistics["ground_truths"][im.name].keys()) == sorted(
            rs_questions
        )


@pytest.mark.django_db  # noqa - C901
def test_score_for_user(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1 = rs.readers_group.user_set.first()

    with capture_on_commit_callbacks(execute=True):
        for i, question in enumerate(rs.questions.all()):
            for j, im in enumerate(rs.images.all()):
                ans = AnswerFactory(
                    question=question, creator=r1, answer=(i + j) % 2 == 0
                )
                ans.images.add(im)

    score = rs.score_for_user(r1)
    assert Answer.objects.filter(is_ground_truth=False).count() == 6
    assert score["score__sum"] == 3.0
    assert score["score__avg"] == 0.5


@pytest.mark.django_db
def test_help_markdown_is_scrubbed(client):
    rs = ReaderStudyFactory(
        help_text_markdown="<b>My Help Text</b><script>naughty</script>"
    )
    u = UserFactory()
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=rs.api_url, user=u)

    assert response.status_code == 200
    assert response.json()["help_text"] == "<p><b>My Help Text</b>naughty</p>"


@pytest.mark.django_db
def test_case_text_is_scrubbed(client):
    u = UserFactory()
    im, im1 = ImageFactory(), ImageFactory()
    rs = ReaderStudyFactory(
        case_text={
            im.name: "<b>My Help Text</b><script>naughty</script>",
            "not an image name": "Shouldn't appear in result",
            im1.name: "Doesn't belong to this study so ignore",
        }
    )
    rs.images.add(im)
    rs.add_reader(u)

    response = get_view_for_user(client=client, url=rs.api_url, user=u)

    assert response.status_code == 200
    # Case should be indexed with the api url
    assert response.json()["case_text"] == {
        im.api_url: "<p><b>My Help Text</b>naughty</p>"
    }


@pytest.mark.django_db
def test_validate_answer():
    u = UserFactory()
    im1, im2, im3 = ImageFactory(), ImageFactory(), ImageFactory()
    rs = ReaderStudyFactory(
        hanging_list=[
            {"main": im1.name, "main-overlay": im3.name},
            {"main": im2.name, "main-overlay": im3.name},
        ]
    )
    rs.images.set([im1, im2, im3])
    rs.add_reader(u)

    q = QuestionFactory(
        reader_study=rs,
        answer_type=Question.AnswerType.BOOL,
        question_text="q1",
    )

    answer = AnswerFactory(creator=u, question=q, answer=True,)
    answer.images.set([im1, im3])

    with pytest.raises(ValidationError) as e:
        Answer.validate(
            creator=u, question=q, answer=True, images=[im1, im3],
        )
        assert (
            e.value.message
            == f"User {u} has already answered this question for this set of images."
        )

    assert (
        Answer.validate(creator=u, question=q, answer=True, images=[im2, im3],)
        is None
    )


@pytest.mark.django_db
def test_validate_hanging_list():
    im1, im2, im3 = ImageFactory(), ImageFactory(), ImageFactory()
    rs = ReaderStudyFactory(
        hanging_list=[
            {"main": im1.name, "main-overlay": im3.name},
            {"main": im2.name, "main-overlay": im3.name},
        ]
    )
    rs.images.set([im1, im2, im3])

    assert rs.hanging_list_valid is False

    rs.validate_hanging_list = False
    assert rs.hanging_list_valid is True
