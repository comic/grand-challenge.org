import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.reader_studies.models import Question
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_reader_can_download_images(client, reverse):
    rs_set = TwoReaderStudies()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(image=im1),
        ComponentInterfaceValueFactory(image=im2),
        ComponentInterfaceValueFactory(image=im3),
        ComponentInterfaceValueFactory(image=im4),
    )

    if reverse:
        for civ in [civ1, civ2, civ3, civ4]:
            civ.readerstudies.add(rs_set.rs1, rs_set.rs2)
        for civ in [civ3, civ4]:
            civ.readerstudies.remove(rs_set.rs1, rs_set.rs2)
        for civ in [civ1, civ2]:
            civ.readerstudies.remove(rs_set.rs2)
    else:
        # Test that adding images works
        rs_set.rs1.civs.add(civ1, civ2, civ3, civ4)
        # Test that removing civages works
        rs_set.rs1.civs.remove(civ3, civ4)

    tests = (
        (None, 200, []),
        (rs_set.creator, 200, []),
        (rs_set.editor1, 200, [im1.pk, im2.pk]),
        (rs_set.reader1, 200, [im1.pk, im2.pk]),
        (rs_set.editor2, 200, []),
        (rs_set.reader2, 200, []),
        (rs_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        assert response.json()["count"] == len(test[2])

        pks = {obj["pk"] for obj in response.json()["results"]}
        assert {str(pk) for pk in test[2]} == pks

    # Test clearing
    if reverse:
        civ1.readerstudies.clear()
        civ2.readerstudies.clear()
    else:
        rs_set.rs1.civs.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=rs_set.reader1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_assign_score(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)
    q1 = QuestionFactory(reader_study=rs)
    q2 = QuestionFactory(
        reader_study=rs, answer_type=Question.AnswerType.MULTIPLE_CHOICE
    )
    e, r1, r2 = UserFactory(), UserFactory(), UserFactory()

    rs.civs.add(civ)
    rs.add_editor(e)
    rs.add_reader(r1)
    rs.add_reader(r2)

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(question=q1, creator=r1, answer="foo")
    a1.civs.add(civ)
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        gt = AnswerFactory(
            question=q1, creator=e, answer="foo", is_ground_truth=True
        )
        gt.civs.add(civ)
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(question=q1, creator=r2, answer="foo")
        a2.civs.add(civ)
    a2.refresh_from_db()
    assert a2.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(question=q2, creator=r1, answer=[])
        a1.civs.add(civ)
    a1.refresh_from_db()
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        gt = AnswerFactory(
            question=q2, creator=e, answer=[], is_ground_truth=True
        )
        gt.civs.add(civ)
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(question=q2, creator=r2, answer=[])
        a2.civs.add(civ)
    a2.refresh_from_db()
    assert a2.score == 1.0
