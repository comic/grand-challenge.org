import pytest
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)


@pytest.fixture
def reader_study_with_gt():
    rs = ReaderStudyFactory()
    im1, im2 = ImageFactory(name="im1"), ImageFactory(name="im2")
    q1, q2, q3 = [
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.ANSWER_TYPE_BOOL,
            question_text="q1",
        ),
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.ANSWER_TYPE_BOOL,
            question_text="q2",
        ),
        QuestionFactory(
            reader_study=rs,
            answer_type=Question.ANSWER_TYPE_BOOL,
            question_text="q3",
        ),
    ]

    r1, r2, editor = UserFactory(), UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_reader(r2)
    rs.add_editor(editor)
    rs.images.set([im1, im2])
    rs.hanging_list = [{"main": im1.name}, {"main": im2.name}]
    rs.save()

    for question in [q1, q2, q3]:
        for im in [im1, im2]:
            ans = AnswerFactory(
                question=question,
                creator=editor,
                answer=True,
                is_ground_truth=True,
            )
            ans.images.add(im)

    return rs


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

    getattr(rs, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        readers_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        rs.refresh_from_db()


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
def test_progress_for_user():
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

    assert rs.get_progress_for_user(reader) is None

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


@pytest.mark.django_db
def test_leaderboard(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()

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

    for i, question in enumerate(rs.questions.all()):
        for j, im in enumerate(rs.images.all()):
            ans = AnswerFactory(
                question=question, creator=r2, answer=(i + j) % 2 == 0
            )
            ans.images.add(im)

    del rs.scores_by_user
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


@pytest.mark.django_db  # noqa - C901
def test_statistics_by_question(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1, r2 = rs.readers_group.user_set.all()

    for question in rs.questions.all():
        for im in rs.images.all():
            ans = AnswerFactory(question=question, creator=r1, answer=True)
            ans.images.add(im)

    statistics = rs.statistics
    assert Answer.objects.filter(is_ground_truth=False).count() == 6
    assert statistics["max_score_questions"] == 2.0
    scores = statistics["scores_by_question"]
    assert len(scores) == rs.questions.count()
    questions = set(rs.questions.values_list("question_text", flat=True))
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

    for question in rs.questions.all():
        for im in rs.images.all():
            answer = question.question_text == "q1" and im.name == "im1"
            ans = AnswerFactory(question=question, creator=r2, answer=answer)
            ans.images.add(im)

    statistics = rs.statistics
    assert Answer.objects.filter(is_ground_truth=False).count() == 12
    assert statistics["max_score_cases"] == 6.0
    scores = statistics["scores_by_question"]
    assert len(scores) == rs.questions.count()
    questions = set(rs.questions.values_list("question_text", flat=True))
    for score in scores:
        questions -= {score["question__question_text"]}
        if score["question__question_text"] == "q1":
            assert score["score__sum"] == 3.0
            assert score["score__avg"] == 0.75
        else:
            assert score["score__sum"] == 2.0
            assert score["score__avg"] == 0.5
    assert questions == set()


@pytest.mark.django_db  # noqa - C901
def test_score_for_user(reader_study_with_gt, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = reader_study_with_gt
    r1 = rs.readers_group.user_set.first()

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
